import os
import re
import json
import secrets
from datetime import datetime, timedelta
from functools import wraps

# Pinned reference clock used by deterministic seed paths (reviews, wishlists).
# Keeps byte-identical reset working even when the host wall clock changes.
MIRROR_REFERENCE_DATE = datetime(2025, 11, 1, 12, 0, 0)

# Pinned bcrypt hash for 'TestPass123!' — keeps benchmark-user password_hash
# bytes stable across rebuilds (bcrypt.generate_password_hash mixes a random
# salt on every call which would shift on-disk SQLite page bytes).
PINNED_PASSWORD_HASH = '$2b$12$RwAC/sfwDHtccU//A20fde.uKkZK4Ptnjjyua2l2ktwI6uysAp3Ou'

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, session, abort, Response
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, PasswordField, BooleanField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///apple_store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    state = db.Column(db.String(50))
    zip_code = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders = db.relationship('Order', backref='user', lazy=True)
    cart_items = db.relationship('CartItem', backref='user', lazy=True)
    wishlist_items = db.relationship('WishlistItem', backref='user', lazy=True)
    reviews = db.relationship('Review', backref='user', lazy=True)
    payment_methods = db.relationship('PaymentMethod', backref='user', lazy=True, cascade='all, delete-orphan')
    saved_addresses = db.relationship('SavedAddress', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(150), unique=True, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # iphone, mac, ipad, watch, airpods, accessories, tv, homepod, vision, audio
    subcategory = db.Column(db.String(60), default='')   # e.g. macbook-pro, macbook-air, ipad-pro, ipad-mini, airpods-pro, airpods-3, vision-pro-accessory
    subtitle = db.Column(db.String(300))
    description = db.Column(db.Text)
    slogan = db.Column(db.String(300), default='')
    price = db.Column(db.Float, nullable=False)
    monthly_price = db.Column(db.Float)
    months = db.Column(db.Integer, default=24)
    image = db.Column(db.String(300))
    hero_image = db.Column(db.String(300))
    color_options = db.Column(db.Text)   # JSON list
    storage_options = db.Column(db.Text) # JSON list (or size options for Watch)
    is_new = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    specs = db.Column(db.Text)           # JSON dict
    in_stock = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Phase 9 task-driven columns
    chip_family = db.Column(db.String(40), default='')     # e.g. M1, M2, M3, M3 Pro, M3 Max, A15, A17 Pro
    ram = db.Column(db.Integer, default=0)                 # GB
    ssd = db.Column(db.Integer, default=0)                 # GB
    screen_size = db.Column(db.Float, default=0.0)         # inches
    connectivity = db.Column(db.String(60), default='')    # Wi-Fi / Wi-Fi + Cellular / LTE / etc
    release_year = db.Column(db.Integer, default=2024)
    release_date = db.Column(db.String(40), default='')
    battery_life = db.Column(db.String(120), default='')   # "18 hours web browsing"
    weight = db.Column(db.String(60), default='')
    video_recording = db.Column(db.String(100), default='')
    processor = db.Column(db.String(80), default='')       # display processor for Apple TV / non-Mac
    gpu_cores = db.Column(db.Integer, default=0)
    cpu_cores = db.Column(db.Integer, default=0)
    feature_tags = db.Column(db.Text, default='[]')        # JSON list – kebab-case tags
    box_contents = db.Column(db.Text, default='[]')        # JSON list
    config_upgrades = db.Column(db.Text, default='{}')     # JSON dict for configurators
    tradein_value = db.Column(db.Float, default=0.0)
    tradein_eligible = db.Column(db.Boolean, default=False)
    support_url = db.Column(db.String(200), default='')
    keyboard_options = db.Column(db.Text, default='[]')    # JSON list (for Mac configurators)
    pickup_zip = db.Column(db.String(20), default='')      # nearest pickup zip
    pickup_available = db.Column(db.Boolean, default=True)

    def get_colors(self):
        try:
            return json.loads(self.color_options) if self.color_options else []
        except Exception:
            return []

    def get_storage(self):
        try:
            return json.loads(self.storage_options) if self.storage_options else []
        except Exception:
            return []

    def get_specs(self):
        try:
            return json.loads(self.specs) if self.specs else {}
        except Exception:
            return {}

    def get_feature_tags(self):
        try:
            return json.loads(self.feature_tags or '[]')
        except Exception:
            return []

    def get_box_contents(self):
        try:
            return json.loads(self.box_contents or '[]')
        except Exception:
            return []

    def get_config_upgrades(self):
        try:
            return json.loads(self.config_upgrades or '{}')
        except Exception:
            return {}

    def get_keyboard_options(self):
        try:
            return json.loads(self.keyboard_options or '[]')
        except Exception:
            return []


class SupportArticle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(150), unique=True, nullable=False)
    topic = db.Column(db.String(80), default='')      # e.g. apple-id, ios, iphone, mac, repair
    title = db.Column(db.String(300), nullable=False)
    summary = db.Column(db.Text, default='')
    body = db.Column(db.Text, default='')
    compat = db.Column(db.Text, default='[]')         # JSON list of compatible devices
    tags = db.Column(db.Text, default='[]')           # JSON list of kebab-case tags
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_compat(self):
        try:
            return json.loads(self.compat or '[]')
        except Exception:
            return []

    def get_tags(self):
        try:
            return json.loads(self.tags or '[]')
        except Exception:
            return []


class TradeInValue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device = db.Column(db.String(150), nullable=False)
    condition = db.Column(db.String(40), default='good')  # good, excellent, fair
    value = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    color = db.Column(db.String(50))
    storage = db.Column(db.String(50))
    memory = db.Column(db.String(80))
    unit_price = db.Column(db.Float)  # configured price (base + storage/memory deltas); fallback to product.price if None
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    product = db.relationship('Product', lazy=True)

    def effective_price(self):
        return self.unit_price if self.unit_price is not None else (self.product.price if self.product else 0)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    status = db.Column(db.String(20), default='processing')  # processing, shipped, delivered, cancelled
    total = db.Column(db.Float, nullable=False)
    shipping_address = db.Column(db.String(300))
    shipping_method = db.Column(db.String(50), default='standard')
    payment_method = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True)


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Float, nullable=False)
    color = db.Column(db.String(50))
    storage = db.Column(db.String(50))
    product = db.relationship('Product', lazy=True)


class WishlistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    product = db.relationship('Product', lazy=True)
    __table_args__ = (db.UniqueConstraint('user_id', 'product_id'),)


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    title = db.Column(db.String(200))
    body = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    product = db.relationship('Product', lazy=True)


class PaymentMethod(db.Model):
    __tablename__ = 'payment_methods'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    card_type = db.Column(db.String(20), nullable=False)   # Visa, Mastercard, Amex
    last4 = db.Column(db.String(4), nullable=False)
    exp_month = db.Column(db.Integer, nullable=False)
    exp_year = db.Column(db.Integer, nullable=False)
    cardholder_name = db.Column(db.String(120), default='')
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SavedAddress(db.Model):
    __tablename__ = 'saved_addresses'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    label = db.Column(db.String(50), default='Home')  # Home, Work, Gift, Other
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(50), nullable=False)
    zip_code = db.Column(db.String(10), nullable=False)
    phone = db.Column(db.String(20), default='')
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------

class LoginForm(FlaskForm):
    email = StringField('Apple ID (Email)', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember me')


class RegisterForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=1, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=1, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])


class CheckoutForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[DataRequired()])
    address = StringField('Address', validators=[DataRequired()])
    city = StringField('City', validators=[DataRequired()])
    state = StringField('State', validators=[DataRequired()])
    zip_code = StringField('ZIP Code', validators=[DataRequired()])
    shipping_method = SelectField('Shipping', choices=[
        ('standard', 'Standard Shipping - Free'),
        ('express', 'Express Shipping - $9.99'),
        ('overnight', 'Overnight Shipping - $19.99'),
    ])
    payment_method = SelectField('Payment', choices=[
        ('apple_pay', 'Apple Pay'),
        ('credit_card', 'Credit Card'),
        ('monthly', 'Monthly Installments'),
    ])


class ProfileForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=1, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=1, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone')
    address = StringField('Address')
    city = StringField('City')
    state = StringField('State')
    zip_code = StringField('ZIP Code')


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm', validators=[DataRequired(), EqualTo('new_password')])


class ReviewForm(FlaskForm):
    rating = SelectField('Rating', choices=[(str(i), f'{i} Star{"s" if i > 1 else ""}') for i in range(5, 0, -1)], validators=[DataRequired()])
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    body = StringField('Review', validators=[DataRequired()])


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------------------------------------------------------------------------
# Context processor - inject cart count into all templates
# ---------------------------------------------------------------------------

def load_gallery(slug):
    """Load product gallery images from JSON."""
    gallery_path = os.path.join(os.path.dirname(__file__), 'product_galleries.json')
    if os.path.exists(gallery_path):
        with open(gallery_path) as f:
            galleries = json.load(f)
        return galleries.get(slug, [])
    return []


@app.context_processor
def inject_cart_count():
    from flask_wtf.csrf import generate_csrf
    if current_user.is_authenticated:
        count = CartItem.query.filter_by(user_id=current_user.id).count()
    else:
        count = len(session.get('cart', []))
    return {'cart_count': count, 'csrf_token_value': generate_csrf()}


# R6 — Breadcrumb + "Why people compare" + "You may also like" injected globally.
_R6_CATEGORY_LABELS = {
    'iphone': ('iPhone', '/iphone'),
    'mac': ('Mac', '/mac'),
    'ipad': ('iPad', '/ipad'),
    'watch': ('Apple Watch', '/watch'),
    'airpods': ('AirPods', '/airpods'),
    'accessories': ('Accessories', '/accessories'),
    'vision': ('Apple Vision Pro', '/vision-pro'),
    'tv': ('Apple TV', '/tv-home'),
    'homepod': ('HomePod', '/accessories'),
    'audio': ('Audio', '/airpods'),
}

_R6_WHY_COMPARE_HINTS = {
    'iphone': [
        'Pro models offer the A19 Pro chip and 48MP telephoto camera; standard models keep the A18 with a dual-camera system.',
        'Battery life ranges from 28 hours (iPhone 17) to 39 hours (iPhone 17 Pro Max) — a 39% difference on heavy video use.',
        'Display sizes step from 6.1" (iPhone 17) to 6.9" (Pro Max) — pick the size that fits your daily carry.',
        'iPhone Air is the thinnest iPhone ever; trade some camera reach for a lighter pocket profile.',
    ],
    'mac': [
        'MacBook Air is fanless and silent; MacBook Pro adds active cooling to sustain peak performance for long renders.',
        'M3 Pro / M3 Max unlock the GPU horsepower for 8K ProRes editing and ML training — M3 base is plenty for everyday work.',
        '13-inch favors portability; 14-inch / 16-inch favor screen real estate, speakers, and battery capacity.',
    ],
    'ipad': [
        'iPad Pro M5 supports Apple Pencil Pro hover + ProMotion 120Hz; iPad and iPad Air keep 60Hz with simpler stylus support.',
        'Cellular variants add eSIM + Find My over LTE/5G — pick Wi-Fi if you mostly tether to iPhone.',
        'Magic Keyboard upgrades make iPad Pro a near-laptop; iPad mini stays at the Smart Folio tier.',
    ],
    'watch': [
        'Apple Watch Ultra 3 adds dive computer + dual-frequency GPS and the largest battery (36-hour with low-power mode).',
        'Series 11 adds Sleep Apnea + Hypertension notifications; SE 2 trades these for a $200 price reduction.',
        'Aluminum vs Stainless Steel vs Titanium changes both weight and finish — pick by sweat and daily wear, not just looks.',
    ],
    'airpods': [
        'AirPods Pro 3 add hearing-aid mode, Hearing Health check, and adaptive ANC tuned for your ear shape.',
        'AirPods Max 2 offer over-ear comfort + Lossless audio over USB-C; AirPods 4 trade noise cancellation for open-fit comfort.',
        'AirPods 4 with ANC sits between AirPods 4 standard and AirPods Pro 3 on noise reduction.',
    ],
}


@app.context_processor
def inject_r6_context():
    """Inject R6 breadcrumb, why-people-compare, and you-may-also-like data
    into every page render. Safe to read on routes that ignore them."""
    try:
        path = (request.path or '/').rstrip('/') or '/'
    except Exception:
        return {}
    crumbs = [{'label': 'Apple', 'url': '/'}]
    why_compare = None
    you_may_like = None
    # /product/<slug>
    if path.startswith('/product/'):
        slug = path.rsplit('/', 1)[-1]
        try:
            p = Product.query.filter_by(slug=slug).first()
        except Exception:
            p = None
        if p:
            cat_label, cat_url = _R6_CATEGORY_LABELS.get(p.category, (p.category.capitalize(), '/shop'))
            crumbs.append({'label': cat_label, 'url': cat_url})
            crumbs.append({'label': p.name, 'url': f'/product/{p.slug}'})
            why_compare = _R6_WHY_COMPARE_HINTS.get(p.category)
            try:
                related = (Product.query.filter_by(category=p.category)
                                  .filter(Product.id != p.id)
                                  .order_by(Product.is_featured.desc(), Product.price.desc())
                                  .limit(4).all())
                you_may_like = [{'name': r.name, 'url': f'/product/{r.slug}', 'price': r.price}
                                for r in related]
            except Exception:
                you_may_like = None
    elif path.startswith('/compare/'):
        cat = path.rsplit('/', 1)[-1]
        cat_label, cat_url = _R6_CATEGORY_LABELS.get(cat, (cat.capitalize(), '/shop'))
        crumbs.append({'label': cat_label, 'url': cat_url})
        crumbs.append({'label': f'Compare {cat_label}', 'url': f'/compare/{cat}'})
        why_compare = _R6_WHY_COMPARE_HINTS.get(cat)
    elif path.startswith('/iphone'):
        crumbs.append({'label': 'iPhone', 'url': '/iphone'})
        why_compare = _R6_WHY_COMPARE_HINTS.get('iphone')
    elif path.startswith('/mac'):
        crumbs.append({'label': 'Mac', 'url': '/mac'})
        why_compare = _R6_WHY_COMPARE_HINTS.get('mac')
    elif path.startswith('/ipad'):
        crumbs.append({'label': 'iPad', 'url': '/ipad'})
        why_compare = _R6_WHY_COMPARE_HINTS.get('ipad')
    elif path.startswith('/watch'):
        crumbs.append({'label': 'Apple Watch', 'url': '/watch'})
        why_compare = _R6_WHY_COMPARE_HINTS.get('watch')
    elif path.startswith('/airpods'):
        crumbs.append({'label': 'AirPods', 'url': '/airpods'})
        why_compare = _R6_WHY_COMPARE_HINTS.get('airpods')
    elif path.startswith('/shop/refurbished'):
        crumbs.append({'label': 'Shop', 'url': '/shop'})
        crumbs.append({'label': 'Refurbished', 'url': '/shop/refurbished'})
    elif path.startswith('/shop'):
        crumbs.append({'label': 'Shop', 'url': '/shop'})
    elif path.startswith('/accessories'):
        crumbs.append({'label': 'Accessories', 'url': '/accessories'})
    elif path.startswith('/support'):
        crumbs.append({'label': 'Support', 'url': '/support'})
    elif path.startswith('/trade-in'):
        crumbs.append({'label': 'Apple Trade In', 'url': '/trade-in'})
    elif path.startswith('/retail'):
        crumbs.append({'label': 'Apple Retail', 'url': '/retail'})
    elif path.startswith('/today'):
        crumbs.append({'label': 'Today at Apple', 'url': '/today'})
    elif path.startswith('/applecare'):
        crumbs.append({'label': 'AppleCare+', 'url': '/applecare'})
    elif path.startswith('/repair'):
        crumbs.append({'label': 'Repair', 'url': '/repair/status'})
    elif path.startswith('/gift-card'):
        crumbs.append({'label': 'Apple Gift Card', 'url': '/gift-card'})
    elif path.startswith('/notify-arrival'):
        crumbs.append({'label': 'Notify When Available', 'url': path})
    elif path.startswith('/configure'):
        crumbs.append({'label': 'Configure', 'url': path})
    elif path.startswith('/wallet'):
        crumbs.append({'label': 'Apple Wallet', 'url': '/wallet/add'})
    elif path.startswith('/family-sharing'):
        crumbs.append({'label': 'Family Sharing', 'url': '/family-sharing'})
    elif path.startswith('/find-my'):
        crumbs.append({'label': 'Find My', 'url': '/find-my'})
    elif path == '/':
        crumbs = None
    if crumbs and len(crumbs) < 2:
        crumbs = None  # don't show "Apple >" alone
    return {
        'r6_breadcrumb': crumbs,
        'r6_why_compare': why_compare,
        'r6_you_may_like': you_may_like,
    }


# ---------------------------------------------------------------------------
# Routes - Pages
# ---------------------------------------------------------------------------

@app.route('/')
def home():
    featured = Product.query.filter_by(is_featured=True).limit(12).all()
    new_products = Product.query.filter_by(is_new=True).limit(8).all()
    return render_template('index.html', featured=featured, new_products=new_products)


@app.route('/iphone')
@app.route('/iphone/')
def iphone():
    products = Product.query.filter_by(category='iphone').all()
    return render_template('iphone.html', products=products)


@app.route('/mac')
@app.route('/mac/')
def mac():
    products = Product.query.filter_by(category='mac').all()
    return render_template('mac.html', products=products)


@app.route('/ipad')
@app.route('/ipad/')
def ipad():
    products = Product.query.filter_by(category='ipad').all()
    return render_template('ipad.html', products=products)


@app.route('/watch')
@app.route('/watch/')
def watch():
    products = Product.query.filter_by(category='watch').all()
    return render_template('watch.html', products=products)


@app.route('/airpods')
@app.route('/airpods/')
def airpods():
    products = Product.query.filter_by(category='airpods').all()
    return render_template('airpods.html', products=products)


@app.route('/accessories')
@app.route('/accessories/')
def accessories():
    products = Product.query.filter_by(category='accessories').all()
    return render_template('accessories.html', products=products)


# ---------------------------------------------------------------------------
# Routes - Store / Shopping
# ---------------------------------------------------------------------------

@app.route('/shop')
@app.route('/shop/')
def shop():
    products = Product.query.all()
    categories = db.session.query(Product.category).distinct().all()
    return render_template('shop.html', products=products, categories=[c[0] for c in categories])


@app.route('/product/<slug>')
def product_detail(slug):
    product = Product.query.filter_by(slug=slug).first_or_404()
    related = Product.query.filter_by(category=product.category).filter(Product.id != product.id).limit(4).all()
    gallery = load_gallery(slug)
    reviews = Review.query.filter_by(product_id=product.id).order_by(Review.created_at.desc()).all()
    avg_rating = db.session.query(db.func.avg(Review.rating)).filter_by(product_id=product.id).scalar()
    in_wishlist = False
    if current_user.is_authenticated:
        in_wishlist = WishlistItem.query.filter_by(user_id=current_user.id, product_id=product.id).first() is not None
    review_form = ReviewForm()
    return render_template('product_detail.html', product=product, related=related,
                           gallery=gallery, reviews=reviews, avg_rating=avg_rating,
                           in_wishlist=in_wishlist, review_form=review_form)


# ---------------------------------------------------------------------------
# Routes - Cart
# ---------------------------------------------------------------------------

@app.route('/bag')
@app.route('/shop/bag')
def bag():
    if current_user.is_authenticated:
        items = CartItem.query.filter_by(user_id=current_user.id).all()
    else:
        items = []
        for ci in session.get('cart', []):
            product = Product.query.get(ci['product_id'])
            if product:
                items.append({
                    'id': ci.get('id', 0),
                    'product': product,
                    'quantity': ci['quantity'],
                    'color': ci.get('color', ''),
                    'storage': ci.get('storage', ''),
                })
    return render_template('bag.html', items=items)


@app.route('/api/cart/add', methods=['POST'])
@csrf.exempt
def cart_add():
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    color = data.get('color', '')
    storage = data.get('storage', '')

    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404

    if current_user.is_authenticated:
        existing = CartItem.query.filter_by(
            user_id=current_user.id, product_id=product_id,
            color=color, storage=storage
        ).first()
        if existing:
            existing.quantity += quantity
        else:
            item = CartItem(user_id=current_user.id, product_id=product_id,
                          quantity=quantity, color=color, storage=storage)
            db.session.add(item)
        db.session.commit()
        count = CartItem.query.filter_by(user_id=current_user.id).count()
    else:
        cart = session.get('cart', [])
        found = False
        for ci in cart:
            if ci['product_id'] == product_id and ci.get('color') == color and ci.get('storage') == storage:
                ci['quantity'] += quantity
                found = True
                break
        if not found:
            cart.append({'product_id': product_id, 'quantity': quantity, 'color': color, 'storage': storage})
        session['cart'] = cart
        count = len(cart)

    return jsonify({'success': True, 'cart_count': count, 'message': f'{product.name} added to bag'})


@app.route('/api/cart/update', methods=['POST'])
@csrf.exempt
def cart_update():
    data = request.get_json()
    item_id = data.get('item_id')
    quantity = data.get('quantity', 1)

    if current_user.is_authenticated:
        item = CartItem.query.get(item_id)
        if item and item.user_id == current_user.id:
            if quantity <= 0:
                db.session.delete(item)
            else:
                item.quantity = quantity
            db.session.commit()
    return jsonify({'success': True})


@app.route('/api/cart/remove', methods=['POST'])
@csrf.exempt
def cart_remove():
    data = request.get_json()
    item_id = data.get('item_id')

    if current_user.is_authenticated:
        item = CartItem.query.get(item_id)
        if item and item.user_id == current_user.id:
            db.session.delete(item)
            db.session.commit()
    else:
        cart = session.get('cart', [])
        cart = [ci for i, ci in enumerate(cart) if i != item_id]
        session['cart'] = cart

    return jsonify({'success': True})


def compute_configured_price(product, storage, memory):
    """Server-authoritative price: base + storage delta + memory delta from product.config_upgrades."""
    price = float(product.price or 0)
    try:
        upgrades = product.get_config_upgrades() or {}
    except Exception:
        upgrades = {}
    for opt in upgrades.get('storage', []) or []:
        if storage and storage in opt.get('label', ''):
            price += float(opt.get('price') or 0)
            break
    for opt in upgrades.get('memory', []) or []:
        if memory and memory == opt.get('label', ''):
            price += float(opt.get('price') or 0)
            break
    return round(price, 2)


@app.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def cart_add_form(product_id):
    """Non-AJAX form POST route for add-to-cart (browser agent friendly)."""
    product = Product.query.get_or_404(product_id)
    color = request.form.get('color', '')
    storage = request.form.get('storage', '')
    memory = request.form.get('memory', '')
    qty = int(request.form.get('quantity', 1))
    unit_price = compute_configured_price(product, storage, memory)
    existing = CartItem.query.filter_by(
        user_id=current_user.id, product_id=product_id,
        color=color, storage=storage, memory=memory
    ).first()
    if existing:
        existing.quantity += qty
        existing.unit_price = unit_price
    else:
        item = CartItem(user_id=current_user.id, product_id=product_id,
                        quantity=qty, color=color, storage=storage,
                        memory=memory, unit_price=unit_price)
        db.session.add(item)
    db.session.commit()
    flash(f'{product.name} added to bag.', 'success')
    return redirect(url_for('bag'))


@app.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def cart_remove_form(item_id):
    """Non-AJAX form POST route for remove-from-cart."""
    item = CartItem.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        abort(403)
    db.session.delete(item)
    db.session.commit()
    flash('Item removed from bag.', 'info')
    return redirect(url_for('bag'))


@app.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def cart_update_form(item_id):
    """Non-AJAX form POST route for update-cart-quantity."""
    item = CartItem.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        abort(403)
    qty = int(request.form.get('quantity', 1))
    if qty <= 0:
        db.session.delete(item)
    else:
        item.quantity = qty
    db.session.commit()
    return redirect(url_for('bag'))


# ---------------------------------------------------------------------------
# Routes - Auth
# ---------------------------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            # Merge session cart into user cart
            cart = session.pop('cart', [])
            for ci in cart:
                existing = CartItem.query.filter_by(
                    user_id=user.id, product_id=ci['product_id']
                ).first()
                if existing:
                    existing.quantity += ci['quantity']
                else:
                    item = CartItem(user_id=user.id, product_id=ci['product_id'],
                                  quantity=ci['quantity'], color=ci.get('color', ''),
                                  storage=ci.get('storage', ''))
                    db.session.add(item)
            db.session.commit()
            next_page = request.args.get('next')
            flash('Signed in successfully.', 'success')
            return redirect(next_page or url_for('home'))
        flash('Invalid email or password.', 'error')
    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash('An account with this email already exists.', 'error')
        else:
            user = User(
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                email=form.email.data.lower()
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash('Account created successfully!', 'success')
            return redirect(url_for('home'))
    return render_template('register.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been signed out.', 'info')
    return redirect(url_for('home'))


@app.route('/account')
@login_required
def account():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    wishlist = WishlistItem.query.filter_by(user_id=current_user.id).all()
    return render_template('account.html', orders=orders, wishlist=wishlist)


@app.route('/account/edit', methods=['GET', 'POST'])
@login_required
def account_edit():
    form = ProfileForm()
    if request.method == 'GET':
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.email.data = current_user.email
        form.phone.data = current_user.phone or ''
        form.address.data = current_user.address or ''
        form.city.data = current_user.city or ''
        form.state.data = current_user.state or ''
        form.zip_code.data = current_user.zip_code or ''
    if form.validate_on_submit():
        # Check email uniqueness
        if form.email.data.lower() != current_user.email:
            existing = User.query.filter_by(email=form.email.data.lower()).first()
            if existing:
                flash('That email is already in use.', 'error')
                return render_template('account_edit.html', form=form)
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.email = form.email.data.lower()
        current_user.phone = form.phone.data
        current_user.address = form.address.data
        current_user.city = form.city.data
        current_user.state = form.state.data
        current_user.zip_code = form.zip_code.data
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
            flash('Current password is incorrect.', 'error')
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Password changed successfully.', 'success')
            return redirect(url_for('account'))
    return render_template('change_password.html', form=form)


@app.route('/account/delete', methods=['POST'])
@login_required
def delete_account():
    uid = current_user.id
    logout_user()
    # Remove related data
    CartItem.query.filter_by(user_id=uid).delete()
    WishlistItem.query.filter_by(user_id=uid).delete()
    Review.query.filter_by(user_id=uid).delete()
    for order in Order.query.filter_by(user_id=uid).all():
        OrderItem.query.filter_by(order_id=order.id).delete()
    Order.query.filter_by(user_id=uid).delete()
    User.query.filter_by(id=uid).delete()
    db.session.commit()
    flash('Your account has been deleted.', 'info')
    return redirect(url_for('home'))


# ---------------------------------------------------------------------------
# Routes - Order Management
# ---------------------------------------------------------------------------

@app.route('/order/<int:order_id>/cancel', methods=['POST'])
@login_required
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        abort(403)
    if order.status not in ('processing',):
        flash('Only processing orders can be cancelled.', 'error')
        return redirect(url_for('order_detail', order_id=order.id))
    order.status = 'cancelled'
    order.updated_at = datetime.utcnow()
    db.session.commit()
    flash(f'Order {order.order_number} has been cancelled.', 'success')
    return redirect(url_for('order_detail', order_id=order.id))


@app.route('/order/<int:order_id>/reorder', methods=['POST'])
@login_required
def reorder(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        abort(403)
    added = 0
    for item in order.items:
        if item.product and item.product.in_stock:
            existing = CartItem.query.filter_by(
                user_id=current_user.id, product_id=item.product_id,
                color=item.color, storage=item.storage
            ).first()
            if existing:
                existing.quantity += item.quantity
            else:
                ci = CartItem(user_id=current_user.id, product_id=item.product_id,
                             quantity=item.quantity, color=item.color, storage=item.storage)
                db.session.add(ci)
            added += 1
    db.session.commit()
    flash(f'{added} item(s) added to your bag.', 'success')
    return redirect(url_for('bag'))


@app.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        abort(403)
    return render_template('order_detail.html', order=order)


# ---------------------------------------------------------------------------
# Routes - Wishlist
# ---------------------------------------------------------------------------

@app.route('/api/wishlist/toggle', methods=['POST'])
@csrf.exempt
def wishlist_toggle():
    if not current_user.is_authenticated:
        return jsonify({'error': 'Sign in required'}), 401
    data = request.get_json()
    product_id = data.get('product_id')
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    existing = WishlistItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'success': True, 'in_wishlist': False, 'message': f'{product.name} removed from wishlist'})
    else:
        wi = WishlistItem(user_id=current_user.id, product_id=product_id)
        db.session.add(wi)
        db.session.commit()
        return jsonify({'success': True, 'in_wishlist': True, 'message': f'{product.name} added to wishlist'})


@app.route('/wishlist')
@login_required
def wishlist():
    items = WishlistItem.query.filter_by(user_id=current_user.id).order_by(WishlistItem.added_at.desc()).all()
    return render_template('wishlist.html', items=items)


@app.route('/wishlist/remove/<int:item_id>', methods=['POST'])
@login_required
def wishlist_remove(item_id):
    item = WishlistItem.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        abort(403)
    db.session.delete(item)
    db.session.commit()
    flash('Removed from wishlist.', 'info')
    return redirect(url_for('wishlist'))


# ---------------------------------------------------------------------------
# Routes - Reviews
# ---------------------------------------------------------------------------

@app.route('/product/<slug>/review', methods=['POST'])
@login_required
def submit_review(slug):
    product = Product.query.filter_by(slug=slug).first_or_404()
    form = ReviewForm()
    if form.validate_on_submit():
        existing = Review.query.filter_by(user_id=current_user.id, product_id=product.id).first()
        if existing:
            existing.rating = int(form.rating.data)
            existing.title = form.title.data
            existing.body = form.body.data
        else:
            review = Review(user_id=current_user.id, product_id=product.id,
                          rating=int(form.rating.data), title=form.title.data, body=form.body.data)
            db.session.add(review)
        db.session.commit()
        flash('Review submitted.', 'success')
    return redirect(url_for('product_detail', slug=slug))


@app.route('/review/<int:review_id>/delete', methods=['POST'])
@login_required
def delete_review(review_id):
    review = Review.query.get_or_404(review_id)
    if review.user_id != current_user.id:
        abort(403)
    slug = review.product.slug
    db.session.delete(review)
    db.session.commit()
    flash('Review deleted.', 'info')
    return redirect(url_for('product_detail', slug=slug))


# ---------------------------------------------------------------------------
# Routes - Saved Addresses
# ---------------------------------------------------------------------------

@app.route('/account/addresses')
@login_required
def saved_addresses():
    addrs = SavedAddress.query.filter_by(user_id=current_user.id).order_by(SavedAddress.is_default.desc()).all()
    return render_template('saved_addresses.html', addresses=addrs)


@app.route('/account/addresses/add', methods=['GET', 'POST'])
@login_required
def add_address():
    if request.method == 'POST':
        label = request.form.get('label', 'Home')
        make_default = request.form.get('is_default') == '1'
        if make_default:
            SavedAddress.query.filter_by(user_id=current_user.id, is_default=True).update({'is_default': False})
        addr = SavedAddress(
            user_id=current_user.id,
            label=label,
            first_name=request.form.get('first_name', ''),
            last_name=request.form.get('last_name', ''),
            address=request.form.get('address', ''),
            city=request.form.get('city', ''),
            state=request.form.get('state', ''),
            zip_code=request.form.get('zip_code', ''),
            phone=request.form.get('phone', ''),
            is_default=make_default,
        )
        db.session.add(addr)
        db.session.commit()
        flash('Address saved.', 'success')
        return redirect(url_for('saved_addresses'))
    return render_template('add_address.html')


@app.route('/account/addresses/<int:addr_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_address(addr_id):
    addr = SavedAddress.query.filter_by(id=addr_id, user_id=current_user.id).first_or_404()
    if request.method == 'POST':
        addr.label = request.form.get('label', addr.label)
        addr.first_name = request.form.get('first_name', addr.first_name)
        addr.last_name = request.form.get('last_name', addr.last_name)
        addr.address = request.form.get('address', addr.address)
        addr.city = request.form.get('city', addr.city)
        addr.state = request.form.get('state', addr.state)
        addr.zip_code = request.form.get('zip_code', addr.zip_code)
        addr.phone = request.form.get('phone', addr.phone)
        make_default = request.form.get('is_default') == '1'
        if make_default:
            SavedAddress.query.filter_by(user_id=current_user.id, is_default=True).update({'is_default': False})
            addr.is_default = True
        db.session.commit()
        flash('Address updated.', 'success')
        return redirect(url_for('saved_addresses'))
    return render_template('add_address.html', address=addr)


@app.route('/account/addresses/<int:addr_id>/delete', methods=['POST'])
@login_required
def delete_address(addr_id):
    addr = SavedAddress.query.filter_by(id=addr_id, user_id=current_user.id).first_or_404()
    db.session.delete(addr)
    db.session.commit()
    flash('Address removed.', 'info')
    return redirect(url_for('saved_addresses'))


@app.route('/account/addresses/<int:addr_id>/set-default', methods=['POST'])
@login_required
def set_default_address(addr_id):
    SavedAddress.query.filter_by(user_id=current_user.id, is_default=True).update({'is_default': False})
    addr = SavedAddress.query.filter_by(id=addr_id, user_id=current_user.id).first_or_404()
    addr.is_default = True
    db.session.commit()
    flash('Default address updated.', 'success')
    return redirect(url_for('saved_addresses'))


# ---------------------------------------------------------------------------
# Routes - Payment Methods
# ---------------------------------------------------------------------------

@app.route('/account/payments')
@login_required
def saved_payments():
    payments = PaymentMethod.query.filter_by(user_id=current_user.id).order_by(PaymentMethod.is_default.desc()).all()
    return render_template('saved_payments.html', payments=payments)


@app.route('/account/payments/add', methods=['GET', 'POST'])
@login_required
def add_payment():
    if request.method == 'POST':
        make_default = request.form.get('is_default') == '1'
        if make_default:
            PaymentMethod.query.filter_by(user_id=current_user.id, is_default=True).update({'is_default': False})
        pm = PaymentMethod(
            user_id=current_user.id,
            card_type=request.form.get('card_type', 'Visa'),
            last4=request.form.get('last4', '0000')[-4:],
            exp_month=int(request.form.get('exp_month', 12)),
            exp_year=int(request.form.get('exp_year', 2027)),
            cardholder_name=request.form.get('cardholder_name', ''),
            is_default=make_default,
        )
        db.session.add(pm)
        db.session.commit()
        flash('Payment method saved.', 'success')
        return redirect(url_for('saved_payments'))
    return render_template('add_payment.html')


@app.route('/account/payments/<int:pm_id>/delete', methods=['POST'])
@login_required
def delete_payment(pm_id):
    pm = PaymentMethod.query.filter_by(id=pm_id, user_id=current_user.id).first_or_404()
    db.session.delete(pm)
    db.session.commit()
    flash('Payment method removed.', 'info')
    return redirect(url_for('saved_payments'))


@app.route('/account/payments/<int:pm_id>/set-default', methods=['POST'])
@login_required
def set_default_payment(pm_id):
    PaymentMethod.query.filter_by(user_id=current_user.id, is_default=True).update({'is_default': False})
    pm = PaymentMethod.query.filter_by(id=pm_id, user_id=current_user.id).first_or_404()
    pm.is_default = True
    db.session.commit()
    flash('Default payment updated.', 'success')
    return redirect(url_for('saved_payments'))


# ---------------------------------------------------------------------------
# Routes - Checkout & Orders
# ---------------------------------------------------------------------------

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not items:
        flash('Your bag is empty.', 'info')
        return redirect(url_for('shop'))

    form = CheckoutForm()
    saved_addrs = SavedAddress.query.filter_by(user_id=current_user.id).order_by(SavedAddress.is_default.desc()).all()
    saved_payments = PaymentMethod.query.filter_by(user_id=current_user.id).order_by(PaymentMethod.is_default.desc()).all()

    # Prefill from user profile
    if request.method == 'GET':
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.email.data = current_user.email
        form.phone.data = current_user.phone or ''
        # Prefill address from default saved address if available
        default_addr = next((a for a in saved_addrs if a.is_default), saved_addrs[0] if saved_addrs else None)
        if default_addr:
            form.address.data = default_addr.address
            form.city.data = default_addr.city
            form.state.data = default_addr.state
            form.zip_code.data = default_addr.zip_code
        else:
            form.address.data = current_user.address or ''
            form.city.data = current_user.city or ''
            form.state.data = current_user.state or ''
            form.zip_code.data = current_user.zip_code or ''

    subtotal = sum(item.effective_price() * item.quantity for item in items)
    shipping_costs = {'standard': 0, 'express': 9.99, 'overnight': 19.99}

    if form.validate_on_submit():
        shipping_cost = shipping_costs.get(form.shipping_method.data, 0)
        total = subtotal + shipping_cost

        # Check for saved address/payment selection
        saved_addr_id = request.form.get('saved_address_id', type=int)
        saved_pm_id = request.form.get('saved_payment_id', type=int)

        if saved_addr_id:
            sa = SavedAddress.query.filter_by(id=saved_addr_id, user_id=current_user.id).first()
            if sa:
                shipping_address = f"{sa.address}, {sa.city}, {sa.state} {sa.zip_code}"
            else:
                shipping_address = f"{form.address.data}, {form.city.data}, {form.state.data} {form.zip_code.data}"
        else:
            shipping_address = f"{form.address.data}, {form.city.data}, {form.state.data} {form.zip_code.data}"

        if saved_pm_id:
            pm = PaymentMethod.query.filter_by(id=saved_pm_id, user_id=current_user.id).first()
            payment_label = f"{pm.card_type} ending in {pm.last4}" if pm else form.payment_method.data
        else:
            payment_label = form.payment_method.data

        order = Order(
            user_id=current_user.id,
            order_number=f"W{secrets.token_hex(5).upper()}",
            total=total,
            shipping_address=shipping_address,
            shipping_method=form.shipping_method.data,
            payment_method=payment_label,
        )
        db.session.add(order)
        db.session.flush()

        for item in items:
            oi = OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.effective_price(),
                color=item.color,
                storage=item.storage,
            )
            db.session.add(oi)
            db.session.delete(item)

        # Update user address
        current_user.phone = form.phone.data
        current_user.address = form.address.data
        current_user.city = form.city.data
        current_user.state = form.state.data
        current_user.zip_code = form.zip_code.data
        db.session.commit()

        return redirect(url_for('order_confirmation', order_id=order.id))

    return render_template('checkout.html', form=form, items=items, subtotal=subtotal,
                         shipping_costs=shipping_costs, saved_addrs=saved_addrs,
                         saved_payments=saved_payments)


@app.route('/order/<int:order_id>/confirmation')
@login_required
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        abort(403)
    return render_template('order_confirmation.html', order=order)


# ---------------------------------------------------------------------------
# Routes - Search
# ---------------------------------------------------------------------------

STOPWORDS = {
    'the', 'a', 'an', 'of', 'in', 'on', 'at', 'to', 'for', 'with',
    'and', 'or', 'is', 'are', 'be', 'by', 'from', 'as', 'that', 'this',
    'on', 'apple', 'find', 'about', 'information', 'page', 'website',
    'check', 'get', 'how', 'much', 'does', 'it', 'cost',
}


def _score_product(product, tokens):
    hay_parts = [
        (product.name or ''),
        (product.category or ''),
        (product.subcategory or ''),
        (product.subtitle or ''),
        (product.description or ''),
        (product.slogan or ''),
        (product.chip_family or ''),
        (product.processor or ''),
        (product.connectivity or ''),
        (product.feature_tags or ''),
        (product.specs or ''),
        (product.color_options or ''),
        (product.storage_options or ''),
    ]
    haystack = ' '.join(hay_parts).lower()
    return sum(1 for t in tokens if t in haystack)


def _apply_product_filters(query_obj):
    category = request.args.get('category', '').strip().lower()
    if category:
        query_obj = query_obj.filter(Product.category == category)

    subcategory = request.args.get('subcategory', '').strip().lower()
    if subcategory:
        query_obj = query_obj.filter(Product.subcategory == subcategory)

    chip = request.args.get('chip', '').strip()
    if chip:
        query_obj = query_obj.filter(Product.chip_family.ilike(f'%{chip}%'))

    min_ram = request.args.get('min_ram', type=int)
    if min_ram is not None:
        query_obj = query_obj.filter(Product.ram >= min_ram)
    min_ssd = request.args.get('min_ssd', type=int)
    if min_ssd is not None:
        query_obj = query_obj.filter(Product.ssd >= min_ssd)

    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    if min_price is not None:
        query_obj = query_obj.filter(Product.price >= min_price)
    if max_price is not None:
        query_obj = query_obj.filter(Product.price <= max_price)

    color = request.args.get('color', '').strip()
    if color:
        query_obj = query_obj.filter(Product.color_options.ilike(f'%{color}%'))

    storage = request.args.get('storage', '').strip()
    if storage:
        query_obj = query_obj.filter(Product.storage_options.ilike(f'%{storage}%'))

    connectivity = request.args.get('connectivity', '').strip()
    if connectivity:
        query_obj = query_obj.filter(Product.connectivity.ilike(f'%{connectivity}%'))

    screen_size = request.args.get('screen_size', type=float)
    if screen_size is not None:
        query_obj = query_obj.filter(Product.screen_size == screen_size)

    release_year = request.args.get('release_year', type=int)
    if release_year is not None:
        query_obj = query_obj.filter(Product.release_year == release_year)

    if request.args.get('in_stock') == '1':
        query_obj = query_obj.filter(Product.in_stock == True)
    if request.args.get('is_new') == '1':
        query_obj = query_obj.filter(Product.is_new == True)

    feature = request.args.get('feature', '').strip().lower()
    if feature:
        tokens = re.findall(r'[a-z0-9][\w-]*', feature)
        for tok in tokens:
            if tok and len(tok) >= 2:
                query_obj = query_obj.filter(Product.feature_tags.ilike(f'%{tok}%'))

    return query_obj


def _apply_sort(results, key):
    if key == 'price_asc':
        return sorted(results, key=lambda p: p.price)
    if key == 'price_desc':
        return sorted(results, key=lambda p: p.price, reverse=True)
    if key == 'newest':
        return sorted(results, key=lambda p: (p.release_year or 0, p.created_at), reverse=True)
    if key == 'screen_size':
        return sorted(results, key=lambda p: p.screen_size or 0, reverse=True)
    if key == 'name':
        return sorted(results, key=lambda p: (p.name or '').lower())
    return results


@app.route('/search')
@app.route('/search/<path:apple_query>')
def search(apple_query=''):
    q = (apple_query or request.args.get('q', '')).strip()
    query_obj = Product.query
    query_obj = _apply_product_filters(query_obj)
    candidates = query_obj.all()

    if q:
        tokens = [t.lower() for t in re.findall(r'[a-z0-9]+', q.lower())
                  if t and t not in STOPWORDS and len(t) >= 2]
        if tokens:
            min_required = max(1, len(tokens) // 2)
            scored = []
            for p in candidates:
                s = _score_product(p, tokens)
                if s >= min_required:
                    scored.append((s, p))
            scored.sort(key=lambda x: -x[0])
            results = [p for _, p in scored]
        else:
            results = candidates
    else:
        results = candidates

    # Also include matching support articles when query present
    articles = []
    if q:
        tokens = [t.lower() for t in re.findall(r'[a-z0-9]+', q.lower())
                  if t and t not in STOPWORDS and len(t) >= 2]
        if tokens:
            for art in SupportArticle.query.all():
                hay = ' '.join([
                    art.title or '', art.summary or '', art.body or '',
                    art.topic or '', art.tags or '', art.compat or ''
                ]).lower()
                if sum(1 for t in tokens if t in hay) >= max(1, len(tokens) // 2):
                    articles.append(art)

    results = _apply_sort(results, request.args.get('sort', ''))
    return render_template('search.html', query=q, results=results, articles=articles)


# ---------------------------------------------------------------------------
# Routes - Support / Trade-In / Store pickup / Music / Vision Pro
# ---------------------------------------------------------------------------

@app.route('/support')
@app.route('/support/')
def support():
    topic = request.args.get('topic', '').strip().lower()
    q = request.args.get('q', '').strip().lower()
    query_obj = SupportArticle.query
    if topic:
        query_obj = query_obj.filter(SupportArticle.topic == topic)
    articles = query_obj.all()
    if q:
        tokens = [t for t in re.findall(r'[a-z0-9]+', q) if t not in STOPWORDS and len(t) >= 2]
        def score(a):
            hay = ' '.join([a.title, a.summary, a.body, a.topic, a.tags, a.compat]).lower()
            return sum(1 for t in tokens if t in hay)
        scored = [(score(a), a) for a in articles]
        scored = [(s, a) for s, a in scored if s >= max(1, len(tokens) // 2)]
        scored.sort(key=lambda x: -x[0])
        articles = [a for _, a in scored]
    # Repair options as first-class content
    repair_options = [
        ('Mail-in repair', 'Ship your device to an Apple Repair Center.'),
        ('Carry-in repair', 'Bring your device to an Apple Store or Apple Authorized Service Provider.'),
        ('Onsite repair (business only)', 'Certain business customers get onsite repair.'),
        ('Express Replacement Service', 'Receive a replacement before sending the original.'),
    ]
    return render_template('support.html', articles=articles, topic=topic, query=q,
                           repair_options=repair_options)


@app.route('/support/article/<slug>')
def support_article(slug):
    # Support both canonical slugs and common alias slugs so URLs in
    # support docs remain resolvable even when users type variations.
    alias_map = {
        'apple-id-forgot-password':   'forgot-apple-id-password',
        'forgot-password':            'forgot-apple-id-password',
        'ios17-new-features':         'ios-17-new-features',
        'ios-17-features':            'ios-17-new-features',
        'repair':                     'apple-repair-options',
        'apple-repair':               'apple-repair-options',
        'trade-in':                   'iphone-trade-in-offers',
    }
    resolved_slug = alias_map.get(slug, slug)
    art = SupportArticle.query.filter_by(slug=resolved_slug).first()
    if not art:
        abort(404)
    return render_template('support_article.html', article=art)


@app.route('/support/repair')
@app.route('/support/repair/')
def support_repair():
    """Dedicated Apple Repair landing page listing every repair option."""
    repair_options = [
        ('Mail-in repair',
         'Ship your device to an Apple Repair Center using a prepaid box.'),
        ('Carry-in repair',
         'Bring your device to an Apple Store or Apple Authorized Service Provider.'),
        ('Onsite repair (business only)',
         'Certain business customers are eligible for onsite repair visits.'),
        ('Express Replacement Service',
         'Receive a replacement device before sending the original back.'),
        ('Self Service Repair',
         'Order Apple-genuine parts, tools, and manuals to repair eligible products yourself.'),
    ]
    # Surface the canonical repair article for deeper reading.
    repair_article = SupportArticle.query.filter_by(slug='apple-repair-options').first()
    return render_template('support_repair.html',
                           repair_options=repair_options,
                           repair_article=repair_article)


@app.route('/support/apple-id-forgot-password')
@app.route('/support/apple-id/forgot-password')
@app.route('/support/forgot-password')
def support_forgot_password():
    """Canonical landing page for the 'forgot Apple ID password' task."""
    art = SupportArticle.query.filter_by(slug='forgot-apple-id-password').first()
    if art:
        return render_template('support_article.html', article=art)
    abort(404)


@app.route('/support/article/ios-17-new-features')
def support_ios17_new_features():
    """Friendly redirect/alias for the iOS 17 features article."""
    art = SupportArticle.query.filter_by(slug='ios-17-new-features').first()
    if art:
        return render_template('support_article.html', article=art)
    abort(404)


@app.route('/trade-in')
@app.route('/trade-in/')
def trade_in():
    device = request.args.get('device', '').strip().lower()
    query_obj = TradeInValue.query
    matches = []
    if device:
        tokens = [t for t in re.findall(r'[a-z0-9]+', device) if t not in STOPWORDS and len(t) >= 2]
        for row in query_obj.all():
            hay = row.device.lower()
            if sum(1 for t in tokens if t in hay) >= max(1, len(tokens) // 2):
                matches.append(row)
    else:
        matches = query_obj.all()
    return render_template('trade_in.html', device=device, matches=matches)


@app.route('/trade-in/<device_slug>')
def trade_in_device(device_slug):
    """Direct trade-in value page for a specific device slug (e.g. iphone-11-pro-max)."""
    slug = (device_slug or '').strip().lower()
    # Map slug -> display-cased device name used in the DB.
    slug_words = [w for w in re.split(r'[-_]+', slug) if w]
    all_rows = TradeInValue.query.all()
    best = None
    best_score = 0
    for row in all_rows:
        hay_tokens = set(re.findall(r'[a-z0-9]+', row.device.lower()))
        score = sum(1 for w in slug_words if w in hay_tokens)
        if score > best_score:
            best_score = score
            best = row
    if not best or best_score < max(1, len(slug_words) // 2):
        # No direct match -> show empty state with search box preseeded.
        return render_template('trade_in.html',
                               device=slug.replace('-', ' '),
                               matches=[])
    return render_template('trade_in.html',
                           device=best.device,
                           matches=[best])


@app.route('/trade-in/quote', methods=['GET', 'POST'])
@csrf.exempt
def trade_in_quote():
    """JSON trade-in quote. Real Apple has a POST -> JSON quote flow; we mirror
    it. Accepts ?device=<model>&condition=<good|fair|broken|excellent>.

    Returns a deterministic value derived from the TradeInValue table — never
    'unknown' for a device we recognize, so multi-step agent tasks always make
    forward progress.
    """
    device = (request.values.get('device') or '').strip()
    condition = (request.values.get('condition') or 'good').strip().lower()
    if not device:
        return jsonify({'error': 'device parameter required',
                        'example': '/trade-in/quote?device=iPhone+13+Pro+Max'}), 400
    # Score every row, pick the best. Single-digit tokens (e.g. "8" in
    # "iPhone 8") are kept — they are the disambiguator between SKUs.
    raw = re.findall(r'[a-z0-9]+', device.lower())
    tokens = [t for t in raw if t not in STOPWORDS and (len(t) >= 2 or t.isdigit())]
    best, best_score = None, 0
    for row in TradeInValue.query.all():
        hay = set(re.findall(r'[a-z0-9]+', row.device.lower()))
        s = sum(1 for t in tokens if t in hay)
        # Tie-breaker: prefer the row whose hay length most-closely matches the
        # query token count (avoids "iPhone 13" matching "iPhone 13 Pro Max").
        if s > best_score or (s == best_score and best is not None
                              and abs(len(hay) - len(tokens)) <
                                  abs(len(set(re.findall(r'[a-z0-9]+', best.device.lower()))) - len(tokens))):
            best, best_score = row, s
    if not best or best_score < max(1, len(tokens) // 2):
        return jsonify({
            'eligible': False,
            'device_query': device,
            'message': 'No trade-in match. Apple recycles this device for free.',
        }), 200
    # Condition multiplier (good = 1.0, excellent = 1.05, fair = 0.7, broken = 0.3).
    mult = {'excellent': 1.05, 'good': 1.0, 'fair': 0.7, 'broken': 0.3}.get(condition, 1.0)
    quoted = round(float(best.value) * mult, 2)
    return jsonify({
        'eligible': True,
        'device_query': device,
        'device_matched': best.device,
        'condition': condition,
        'estimated_value_usd': quoted,
        'max_value_usd': float(best.value),
        'gift_card_or_credit': 'Apple Gift Card or instant credit toward a new Apple product',
        'notes': best.notes or '',
    }), 200


@app.route('/store/pickup')
def store_pickup():
    zip_code = request.args.get('zip', '').strip()
    product_slug = request.args.get('product', '').strip()
    pickup_date = request.args.get('date', '').strip()
    selected_store = request.args.get('store', '').strip()
    product = Product.query.filter_by(slug=product_slug).first() if product_slug else None
    nearby_stores = [
        {'name': 'Apple The Grove', 'city': 'Los Angeles', 'zip': '90036', 'distance': '0.8 miles',
         'address': '189 The Grove Drive, Los Angeles, CA 90036'},
        {'name': 'Apple Beverly Center', 'city': 'Los Angeles', 'zip': '90048', 'distance': '1.5 miles',
         'address': '8500 Beverly Blvd, Los Angeles, CA 90048'},
        {'name': 'Apple Century City', 'city': 'Los Angeles', 'zip': '90067', 'distance': '3.2 miles',
         'address': '10250 Santa Monica Blvd, Los Angeles, CA 90067'},
    ]
    # Generate a short list of available pickup dates (today .. +10 days).
    # Also allow any user-supplied YYYY-MM-DD in `date` so scheduling for
    # specific past or future dates (e.g. Jan 10, 2024) is always possible.
    from datetime import timedelta as _td
    today = datetime.utcnow().date()
    available_dates = [(today + _td(days=i)).isoformat() for i in range(11)]
    confirmed = False
    if pickup_date and selected_store:
        confirmed = True
    return render_template('store_pickup.html',
                           zip_code=zip_code, product=product,
                           nearby_stores=nearby_stores,
                           available_dates=available_dates,
                           pickup_date=pickup_date,
                           selected_store=selected_store,
                           confirmed=confirmed)


@app.route('/store/pickup/confirm', methods=['POST'])
@csrf.exempt
def store_pickup_confirm():
    """Confirm an in-store pickup for a given product, store, and date.
    Accepts any date (past or future) so tasks like 'schedule for Jan 10, 2024'
    are always fulfillable, even when that date is in the past."""
    product_slug = request.form.get('product', '').strip()
    zip_code = request.form.get('zip', '').strip()
    store_name = request.form.get('store', '').strip()
    pickup_date = request.form.get('date', '').strip()
    # Pass through GET to render the confirmation state.
    return redirect(url_for('store_pickup',
                            product=product_slug,
                            zip=zip_code,
                            store=store_name,
                            date=pickup_date))


@app.route('/music')
@app.route('/music/')
def apple_music():
    featured_artists = [
        'Taylor Swift', 'Drake', 'The Weeknd', 'Billie Eilish', 'Dua Lipa',
        'Olivia Rodrigo', 'Bad Bunny', 'Harry Styles',
    ]
    return render_template('apple_music.html', artists=featured_artists)


@app.route('/vision-pro')
@app.route('/vision-pro/')
def vision_pro():
    product = Product.query.filter_by(slug='apple-vision-pro').first()
    accessories_list = Product.query.filter_by(subcategory='vision-pro-accessory').all()
    return render_template('vision_pro.html', product=product, accessories=accessories_list)


# ---------------------------------------------------------------------------
# Static info pages (about / business / education / sitemap / help / ...).
# Real apple.com surfaces them under top-level slugs; we provide a single
# template (info_page.html) keyed on the requested topic so every link in the
# footer / global nav resolves to a real, content-bearing page.
# ---------------------------------------------------------------------------

INFO_PAGES = {
    'about': {
        'title': 'About Apple',
        'subtitle': 'Innovation is in our DNA.',
        'body': [
            'Apple revolutionized personal technology with the introduction of the Macintosh in 1984.',
            'Today, Apple leads the world in innovation with iPhone, iPad, Mac, Apple Watch, and Apple Vision Pro.',
            "Apple's five software platforms — iOS, iPadOS, macOS, watchOS, and visionOS — provide seamless experiences across all Apple devices.",
            'Apple is committed to leaving the world better than we found it. By 2030, every Apple product will be carbon neutral.',
        ],
        'links': [
            ('Apple Leadership', '#'),
            ('Career Opportunities', '#'),
            ('Investor Relations', '#'),
            ('Apple Newsroom', '#'),
        ],
    },
    'business': {
        'title': 'Apple at Work',
        'subtitle': 'Empowering every person to do their best work.',
        'body': [
            'Apple products give every employee the freedom to work the way they work best, while saving IT time and budget.',
            'Apple Business Manager lets IT manage devices, apps, and content from a single web-based portal.',
            'Apple Business Essentials is an all-in-one subscription that combines device management, 24/7 Apple support, and iCloud storage for up to 500 employees.',
            'Contact an Apple Business Specialist at 1-800-854-3680, Monday – Friday 7 AM – 5 PM PT.',
        ],
        'links': [
            ('Apple Business Manager', '#'),
            ('Apple Business Essentials', '#'),
            ('Volume Purchase Program', '#'),
            ('Custom Apps for Business', '#'),
        ],
    },
    'education-pricing': {
        'title': 'Education Pricing',
        'subtitle': 'Save on Mac and iPad.',
        'body': [
            'College students, parents buying for college students, and teachers are eligible for education pricing on Mac, iPad, AppleCare, and accessories.',
            'Save up to $200 on Mac and up to $100 on iPad with education pricing.',
            'Get AirPods on us when you buy an eligible Mac or iPad with education pricing.',
            'Verify your status using UNiDAYS at checkout; eligibility is verified automatically.',
        ],
        'links': [
            ('Shop Mac for Education', '/mac'),
            ('Shop iPad for Education', '/ipad'),
            ('Apple Pencil for Students', '/product/apple-pencil-pro'),
            ('AppleCare for Education', '#'),
        ],
    },
    'help': {
        'title': 'Shopping Help',
        'subtitle': 'Get help from a Specialist.',
        'body': [
            'Chat with an Apple Specialist online or call 1-800-MY-APPLE (1-800-692-7753) for advice and ordering.',
            'Returns: All purchases include free 14-day returns. Apple Card customers may pay nothing up front and choose monthly installments.',
            'Shipping: Standard shipping is free on every order. Order before 5 PM for next-day delivery on most in-stock items.',
            'Trade In: Get credit toward a new Apple product when you trade in your eligible device.',
        ],
        'links': [
            ('Order Status', '/account'),
            ('Apple Trade In', '/trade-in'),
            ('Find a Store', '/shop'),
            ('Sign in to Apple ID', '/login'),
        ],
    },
    'accessibility': {
        'title': 'Accessibility',
        'subtitle': 'Made for everyone.',
        'body': [
            'Apple products are designed to give everyone the power to create, learn, communicate, and stay healthy.',
            'Vision features include VoiceOver, Zoom, Magnifier, Spoken Content, and Live Speech.',
            'Hearing features include Made for iPhone Hearing Aids, Live Captions, Sound Recognition, and RTT/TTY support.',
            'Mobility features include AssistiveTouch, Voice Control, Switch Control, and Eye Tracking on iPad and iPhone.',
            'Cognitive features include Assistive Access, Guided Access, Background Sounds, and Personal Voice.',
        ],
        'links': [
            ('Vision Accessibility', '/support/article/accessibility-features'),
            ('Hearing Accessibility', '/support/article/accessibility-features'),
            ('Mobility Accessibility', '/support/article/accessibility-features'),
            ('Cognitive Accessibility', '/support/article/accessibility-features'),
        ],
    },
    'environment': {
        'title': 'Environment',
        'subtitle': 'Carbon neutral by 2030.',
        'body': [
            'Apple is committed to being carbon neutral across our entire footprint, including supply chain and product life cycle, by 2030.',
            'Every Apple product has a smaller carbon footprint than the previous generation.',
            'Apple Vision Pro, Apple Watch, MacBook Air, and iMac use 100% recycled aluminum in the enclosure.',
            'Apple uses 100% recycled rare earth elements in many magnets, including those in iPhone, MacBook, and Apple Watch.',
        ],
        'links': [
            ('Apple Trade In', '/trade-in'),
            ('Recycle for free', '#'),
            ('Environmental Progress Report', '#'),
            ('Materials and Resources', '#'),
        ],
    },
    'sitemap': {
        'title': 'Apple Sitemap',
        'subtitle': 'Every section of apple.com.',
        'body': [
            'A complete index of Apple product pages, support, and services.',
        ],
        'links': [
            ('Store', '/shop'), ('Mac', '/mac'), ('iPad', '/ipad'),
            ('iPhone', '/iphone'), ('Apple Watch', '/watch'), ('AirPods', '/airpods'),
            ('Apple Vision Pro', '/vision-pro'), ('Accessories', '/accessories'),
            ('Apple TV+', '#'), ('Apple Music', '/music'), ('Apple Arcade', '#'),
            ('Support', '/support'), ('Repair', '/support/repair'),
            ('Apple Trade In', '/trade-in'), ('Compare iPhone', '/compare/iphone'),
            ('Compare Mac', '/compare/mac'), ('Compare iPad', '/compare/ipad'),
            ('Compare Apple Watch', '/compare/watch'), ('About Apple', '/about'),
            ('Apple at Work', '/business'), ('Education Pricing', '/education-pricing'),
            ('Accessibility', '/accessibility'), ('Environment', '/environment'),
            ('Privacy', '#'), ('Apple Leadership', '#'),
            ('Career Opportunities', '#'), ('Investor Relations', '#'),
        ],
    },
    'tv-home': {
        'title': 'TV & Home',
        'subtitle': 'A whole new way to enjoy entertainment.',
        'body': [
            'Apple TV 4K delivers cinematic experiences with 4K HDR, Dolby Vision, and Dolby Atmos.',
            'HomePod fills the room with high-fidelity audio that adapts to its surroundings.',
            'HomePod mini delivers room-filling sound from a compact design.',
            'Use the Home app to control HomeKit-enabled accessories with Siri.',
        ],
        'links': [
            ('Apple TV 4K', '/product/apple-tv-4k'),
            ('HomePod (2nd generation)', '/product/homepod-2'),
            ('HomePod mini', '/product/homepod-mini'),
            ('Siri Remote', '/product/apple-tv-remote'),
        ],
    },
    'entertainment': {
        'title': 'Entertainment',
        'subtitle': 'Movies, TV, music, games, news, and more.',
        'body': [
            'Apple TV+ is home to award-winning Apple Originals.',
            'Apple Music has more than 100 million songs and 30,000 expertly curated playlists.',
            'Apple Arcade offers a growing collection of more than 200 incredibly fun games — no ads, no in-app purchases.',
            'News+ unlocks hundreds of premium magazines and leading newspapers.',
        ],
        'links': [
            ('Apple TV+', '#'),
            ('Apple Music', '/music'),
            ('Apple Arcade', '#'),
            ('Apple News+', '#'),
            ('Apple Fitness+', '#'),
            ('Apple One', '/apple-one'),
        ],
    },
    'find-my': {
        'title': 'Find My',
        'subtitle': 'Lose your knack for losing things.',
        'body': [
            'Find My helps you locate your Apple devices, AirTag, and friends — all from one app.',
            'Use Find My iPhone to play a sound on a misplaced device, mark it as lost, or erase it remotely.',
            'AirTag uses Precision Finding with Ultra Wideband to guide you to your item with on-screen directions on iPhone 11 and later.',
            'The Find My network is end-to-end encrypted and anonymous — only you can see the location of your devices.',
            'Find My works with AirPods, Apple Watch, MacBook, iPad, HomePod, and Find My-enabled third-party accessories.',
        ],
        'links': [
            ('AirTag', '/product/airtag'),
            ('AirTag 4 Pack', '/product/airtag-4-pack'),
            ('Set up Find My', '/support/article/find-my-setup'),
            ('Find My network accessories', '#'),
        ],
    },
    'family-sharing': {
        'title': 'Family Sharing',
        'subtitle': 'Share with family. Privately.',
        'body': [
            'Family Sharing makes it easy for up to six people in your family to share App Store purchases, Apple subscriptions, iCloud+ storage, an Apple Music family plan, and more — without sharing accounts.',
            'Ask to Buy lets a parent or guardian approve children\'s purchases or free downloads from a connected device.',
            'Share a family photo album, calendar, and reminders. Find family members on a map with Find My.',
            'Screen Time provides activity reports and lets you set limits on apps and content for children\'s devices.',
            'Share Apple One Family or Apple One Premier across the household with a single payment.',
        ],
        'links': [
            ('Set up Family Sharing', '/support/article/family-sharing-setup'),
            ('Apple One Family', '/product/apple-one-family'),
            ('Apple One Premier', '/product/apple-one-premier'),
            ('iCloud+ Storage', '/product/icloud-200gb'),
        ],
    },
    'applecare': {
        'title': 'AppleCare+',
        'subtitle': 'Coverage that grows with you.',
        'body': [
            'AppleCare+ provides 24/7 priority access to Apple experts and includes unlimited incidents of accidental damage protection.',
            'Choose monthly billing or pay up front for 2 or 3 years of coverage. Cancel anytime.',
            'Add Theft and Loss for iPhone — covers up to two theft or loss incidents over the coverage term.',
            'For Mac, AppleCare+ extends hardware coverage to three years and includes Mac battery service.',
        ],
        'links': [
            ('AppleCare+ for iPhone 17 Pro', '/product/applecare-iphone-17-pro'),
            ('AppleCare+ for MacBook Pro 14"', '/product/applecare-macbook-pro-14'),
            ('AppleCare+ for iPad Pro 13"', '/product/applecare-ipad-pro-13'),
            ('AppleCare+ for Apple Watch Ultra 3', '/product/applecare-watch-ultra-3'),
            ('AppleCare+ for Apple Vision Pro', '/product/applecare-vision-pro'),
            ('Compare AppleCare plans', '/applecare-compare'),
        ],
    },
    'applecare-compare': {
        'title': 'Compare AppleCare+ plans',
        'subtitle': 'See what AppleCare+ covers across iPhone, Mac, iPad, Watch, and Vision Pro.',
        'body': [
            'iPhone — AppleCare+ from $7.99/mo. AppleCare+ with Theft and Loss from $13.49/mo.',
            'iPad — AppleCare+ from $3.99/mo. 2 years of hardware coverage with unlimited accidental damage.',
            'Mac — AppleCare+ from $4.49/mo (Mac mini) up to $26.99/mo (Mac Pro). 3 years of coverage.',
            'Apple Watch — AppleCare+ from $2.49/mo (SE) up to $4.99/mo (Ultra 3). 2 years.',
            'Apple Vision Pro — AppleCare+ at $29.99/mo or $499 for 2 years upfront.',
            'AirPods, HomePod, Apple TV — AppleCare+ from $1.49/mo. 2 years of coverage.',
        ],
        'links': [
            ('Shop AppleCare+ for iPhone', '/product/applecare-iphone-17-pro'),
            ('Shop AppleCare+ for Mac',   '/product/applecare-macbook-pro-16'),
            ('Shop AppleCare+ for iPad',  '/product/applecare-ipad-pro-13'),
            ('Shop AppleCare+ for Watch', '/product/applecare-watch-ultra-3'),
            ('Shop AppleCare+ for Vision Pro', '/product/applecare-vision-pro'),
        ],
    },
    'financing': {
        'title': 'Apple Card Monthly Installments',
        'subtitle': 'Pay over time, interest free.',
        'body': [
            'Apple Card Monthly Installments lets you pay for select Apple products over 12 to 24 months at 0% APR.',
            'iPhone, Mac, iPad, and Apple Watch are eligible for monthly installments with no interest.',
            'See your monthly payment estimate on each product page (e.g. iPhone 17 Pro at $45.79/mo. for 24 months).',
            'Apple Card is required and is subject to credit approval. Variable APRs for Apple Card other than ACMI range from 19.24% to 29.49%.',
        ],
        'links': [
            ('iPhone monthly payment',          '/financing/iphone-monthly-payment'),
            ('Mac monthly payment',             '/financing/mac-monthly-payment'),
            ('iPad monthly payment',            '/financing/ipad-monthly-payment'),
            ('Apple Watch monthly payment',     '/financing/watch-monthly-payment'),
            ('Apple Card',                      '#'),
        ],
    },
    'apple-intelligence': {
        'title': 'Apple Intelligence',
        'subtitle': 'AI for the rest of us.',
        'body': [
            'Apple Intelligence is the personal intelligence system that combines the power of generative models with personal context to deliver helpful and relevant intelligence.',
            'Writing Tools help you rewrite, proofread, and summarize text — across Mail, Notes, Pages, and third-party apps.',
            'Genmoji and Image Playground let you generate custom emoji and images that match your conversation.',
            'Siri gains richer language understanding, on-screen awareness, and ChatGPT integration powered by Apple\'s on-device and Private Cloud Compute models.',
            'Apple Intelligence requires iPhone 15 Pro or later, or iPad/Mac with M1 or later, with Siri and device language set to a supported language.',
        ],
        'links': [
            ('Compatible iPhone', '/compare/iphone'),
            ('Compatible iPad',   '/compare/ipad'),
            ('Compatible Mac',    '/compare/mac'),
            ('Apple Intelligence features', '/support/article/apple-intelligence-features'),
        ],
    },
    'apple-one': {
        'title': 'Apple One',
        'subtitle': 'Bundle Apple services and save.',
        'body': [
            'Individual — Apple Music, Apple TV+, Apple Arcade, and 50GB of iCloud+ for $19.95/mo.',
            'Family — Everything in Individual plus 200GB of iCloud+ for up to 6 family members for $25.95/mo.',
            'Premier — All Family services plus Apple News+, Apple Fitness+, and 2TB of iCloud+ for $37.95/mo.',
            'Try Apple One free for one month. New subscribers only. Plan automatically renews.',
            'Switch between Individual, Family, and Premier at any time in Settings on iPhone, iPad, or Mac.',
        ],
        'links': [
            ('Apple One Individual', '/product/apple-one-individual'),
            ('Apple One Family',     '/product/apple-one-family'),
            ('Apple One Premier',    '/product/apple-one-premier'),
        ],
    },
    'business-program': {
        'title': 'Apple at Work — Volume Pricing',
        'subtitle': 'Volume purchasing for organizations.',
        'body': [
            'Save on bulk Mac, iPad, iPhone, and accessories purchases with Apple Business Pricing.',
            'Order 10 or more Macs, iPads, or iPhones and qualify for volume pricing with Apple Financial Services lease options.',
            'Apple Business Specialists work with IT teams to plan deployments using Apple Business Manager and zero-touch setup.',
            'Contact 1-800-854-3680, 7 AM – 5 PM PT, or request a quote online for orders over $10,000.',
        ],
        'links': [
            ('Mac for business',  '/mac'),
            ('iPad for business', '/ipad'),
            ('iPhone for business','/iphone'),
            ('Request a quote',   '/business/quote'),
            ('Apple Business Manager', '#'),
        ],
    },
}


@app.route('/about')
@app.route('/about/')
@app.route('/business')
@app.route('/business/')
@app.route('/education-pricing')
@app.route('/education-pricing/')
@app.route('/help')
@app.route('/help/')
@app.route('/accessibility')
@app.route('/accessibility/')
@app.route('/environment')
@app.route('/environment/')
@app.route('/sitemap')
@app.route('/sitemap/')
@app.route('/tv-home')
@app.route('/tv-home/')
@app.route('/entertainment')
@app.route('/entertainment/')
@app.route('/find-my')
@app.route('/find-my/')
@app.route('/family-sharing')
@app.route('/family-sharing/')
@app.route('/applecare')
@app.route('/applecare/')
@app.route('/applecare-compare')
@app.route('/applecare-compare/')
@app.route('/financing')
@app.route('/financing/')
@app.route('/apple-intelligence')
@app.route('/apple-intelligence/')
@app.route('/apple-one')
@app.route('/apple-one/')
@app.route('/business-program')
@app.route('/business-program/')
def info_page():
    """Render any registered static info topic via a single Jinja template."""
    # The path strips leading slash + trailing slash, then maps to INFO_PAGES.
    topic = request.path.strip('/').rstrip('/')
    page = INFO_PAGES.get(topic)
    if not page:
        abort(404)
    return render_template('info_page.html', topic=topic, page=page)


# ---------------------------------------------------------------------------
# Financing — per-category monthly-payment summary pages (R3)
# ---------------------------------------------------------------------------

FINANCING_BLURBS = {
    'iphone': ('iPhone monthly payment',
               'Buy the new iPhone with Apple Card Monthly Installments. 0% APR for 24 months.',
               ['iPhone 17 Pro from $45.79/mo. for 24 months.',
                'iPhone 17 Pro Max from $49.95/mo. for 24 months.',
                'iPhone Air from $41.62/mo. for 24 months.',
                'iPhone 17 from $33.29/mo. for 24 months.',
                'iPhone 17e from $24.95/mo. for 24 months.']),
    'mac':    ('Mac monthly payment',
               'Buy a Mac and pay monthly with Apple Card Monthly Installments.',
               ['MacBook Air 13" from $45.79/mo. for 24 months.',
                'MacBook Air 15" from $54.12/mo. for 24 months.',
                'MacBook Pro 14" from $70.79/mo. for 24 months.',
                'MacBook Pro 16" from $104.12/mo. for 24 months.',
                'iMac 24" from $54.12/mo. for 24 months.',
                'Mac mini M4 from $24.95/mo. for 24 months.']),
    'ipad':   ('iPad monthly payment',
               'Pay over time, interest free, with Apple Card Monthly Installments.',
               ['iPad Pro M5 from $41.62/mo. for 24 months.',
                'iPad Air M4 from $24.95/mo. for 24 months.',
                'iPad (A16) from $14.54/mo. for 24 months.',
                'iPad mini from $20.79/mo. for 24 months.']),
    'watch':  ('Apple Watch monthly payment',
               'Pay over time on Apple Watch. 0% APR for 24 months.',
               ['Apple Watch Series 11 from $16.62/mo. for 24 months.',
                'Apple Watch Ultra 3 from $33.29/mo. for 24 months.',
                'Apple Watch SE from $10.37/mo. for 24 months.']),
}


@app.route('/financing/iphone-monthly-payment')
@app.route('/financing/mac-monthly-payment')
@app.route('/financing/ipad-monthly-payment')
@app.route('/financing/watch-monthly-payment')
def financing_monthly_payment():
    """Per-category Apple Card Monthly Installments summary."""
    last = request.path.rstrip('/').rsplit('/', 1)[-1]
    cat = last.split('-monthly-payment')[0]
    if cat not in FINANCING_BLURBS:
        abort(404)
    title, subtitle, lines = FINANCING_BLURBS[cat]
    page = {
        'title': title, 'subtitle': subtitle,
        'body': ['Apple Card Monthly Installments (ACMI) is a 0% APR payment option available only in the U.S. for select Apple products.',
                 *lines,
                 'Variable APRs for Apple Card other than ACMI range from 19.24% to 29.49%.'],
        'links': [('Shop ' + cat.capitalize(), '/' + cat),
                  ('Apple Card', '#'),
                  ('All financing options', '/financing')],
    }
    return render_template('info_page.html', topic=f'financing/{last}', page=page)


@app.route('/business/quote', methods=['GET', 'POST'])
def business_quote():
    """Apple at Work — request a business quote (R3). Stateless info form."""
    submitted = False
    if request.method == 'POST':
        # No DB write — keeps the seed deterministic; this is a contact form.
        submitted = True
    page = {
        'title': 'Request a business quote',
        'subtitle': 'Get help from an Apple Business Specialist.',
        'body': [
            'Apple Business Specialists work with organizations of every size on volume orders, financing, and deployment.',
            'Tell us about your business — number of employees, products of interest, and timeline — and a Specialist will follow up within one business day.',
            'For immediate assistance, call 1-800-854-3680 Monday – Friday, 7 AM – 5 PM PT.',
        ],
        'links': [('Apple Business Manager', '#'),
                  ('Apple Business Essentials', '#'),
                  ('Volume Pricing', '/business-program'),
                  ('Education Pricing', '/education-pricing')],
    }
    if submitted:
        page['body'] = ['Thanks — an Apple Business Specialist will reach out within one business day.'] + page['body']
    return render_template('info_page.html', topic='business/quote', page=page)


# ---------------------------------------------------------------------------
# R4 sub-pages: retail / today-at-apple / refurbished shop / accessibility
# All views are read-only and use module-level constants so they don't
# perturb the seed DB (byte-identical reset stays valid).
# ---------------------------------------------------------------------------

APPLE_RETAIL_STORES = [
    # (slug, name, city_slug, city, state, zip, address, phone, hours)
    ('the-grove',       'Apple The Grove',        'los-angeles',    'Los Angeles',  'CA', '90036', '189 The Grove Drive',           '(323) 617-8205', 'Mon-Sat 10:00-21:00, Sun 11:00-19:00'),
    ('beverly-center',  'Apple Beverly Center',   'los-angeles',    'Los Angeles',  'CA', '90048', '8500 Beverly Blvd',             '(310) 360-2470', 'Mon-Sat 10:00-21:00, Sun 11:00-19:00'),
    ('century-city',    'Apple Century City',     'los-angeles',    'Los Angeles',  'CA', '90067', '10250 Santa Monica Blvd',       '(310) 282-5310', 'Mon-Sat 10:00-21:00, Sun 11:00-19:00'),
    ('union-square',    'Apple Union Square',     'san-francisco',  'San Francisco','CA', '94108', '300 Post Street',               '(415) 486-4800', 'Mon-Sat 09:00-20:00, Sun 10:00-19:00'),
    ('palo-alto',       'Apple Palo Alto',        'palo-alto',      'Palo Alto',    'CA', '94301', '340 University Avenue',         '(650) 798-1450', 'Mon-Sat 10:00-21:00, Sun 11:00-19:00'),
    ('stanford',        'Apple Stanford',         'palo-alto',      'Palo Alto',    'CA', '94304', '660 Stanford Shopping Center',  '(650) 384-2900', 'Mon-Sat 10:00-21:00, Sun 11:00-18:00'),
    ('fifth-avenue',    'Apple Fifth Avenue',     'new-york',       'New York',     'NY', '10153', '767 Fifth Avenue',              '(212) 336-1440', 'Open 24 hours'),
    ('grand-central',   'Apple Grand Central',    'new-york',       'New York',     'NY', '10017', '45 Grand Central Terminal',     '(212) 284-1800', 'Mon-Sat 07:00-21:00, Sun 09:00-21:00'),
    ('soho',            'Apple SoHo',             'new-york',       'New York',     'NY', '10012', '103 Prince Street',             '(212) 226-3126', 'Mon-Sat 09:00-21:00, Sun 10:00-19:00'),
    ('michigan-avenue', 'Apple Michigan Avenue',  'chicago',        'Chicago',      'IL', '60611', '401 N Michigan Avenue',         '(312) 529-9500', 'Mon-Sat 09:00-21:00, Sun 10:00-19:00'),
    ('boylston-street', 'Apple Boylston Street',  'boston',         'Boston',       'MA', '02116', '815 Boylston Street',           '(617) 385-9400', 'Mon-Sat 10:00-21:00, Sun 11:00-19:00'),
    ('georgetown',      'Apple Georgetown',       'washington-dc',  'Washington',   'DC', '20007', '1229 Wisconsin Avenue NW',      '(202) 572-1460', 'Mon-Sat 10:00-21:00, Sun 11:00-19:00'),
    ('aventura',        'Apple Aventura',         'miami',          'Miami',        'FL', '33180', '19565 Biscayne Boulevard',      '(305) 466-4760', 'Mon-Sat 10:00-21:00, Sun 11:00-19:00'),
    ('lincoln-road',    'Apple Lincoln Road',     'miami',          'Miami Beach',  'FL', '33139', '1100 Lincoln Road',             '(305) 421-0900', 'Mon-Sat 10:00-22:00, Sun 11:00-21:00'),
    ('university-village','Apple University Village','seattle',     'Seattle',      'WA', '98105', '2624 NE University Village',    '(206) 526-2580', 'Mon-Sat 10:00-21:00, Sun 11:00-19:00'),
    ('downtown-seattle','Apple Downtown Seattle', 'seattle',        'Seattle',      'WA', '98101', '1632 6th Avenue',               '(206) 264-0900', 'Mon-Sat 10:00-21:00, Sun 11:00-19:00'),
    ('twelve-oaks',     'Apple Twelve Oaks',      'novi',           'Novi',         'MI', '48377', '27500 Novi Road',               '(248) 735-6700', 'Mon-Sat 10:00-21:00, Sun 11:00-19:00'),
    ('lenox-square',    'Apple Lenox Square',     'atlanta',        'Atlanta',      'GA', '30326', '3393 Peachtree Road NE',        '(404) 264-2400', 'Mon-Sat 10:00-21:00, Sun 12:00-18:00'),
    ('domain-northside','Apple Domain Northside', 'austin',         'Austin',       'TX', '78758', '11506 Century Oaks Terrace',    '(512) 873-7100', 'Mon-Sat 10:00-21:00, Sun 11:00-19:00'),
    ('northpark',       'Apple NorthPark',        'dallas',         'Dallas',       'TX', '75225', '8687 N Central Expressway',     '(214) 369-0700', 'Mon-Sat 10:00-21:00, Sun 12:00-18:00'),
    ('biltmore',        'Apple Biltmore',         'phoenix',        'Phoenix',      'AZ', '85016', '2502 E Camelback Road',         '(602) 553-3900', 'Mon-Sat 10:00-21:00, Sun 11:00-19:00'),
    ('park-meadows',    'Apple Park Meadows',     'denver',         'Lone Tree',    'CO', '80124', '8405 Park Meadows Center Dr',   '(303) 410-9600', 'Mon-Sat 10:00-21:00, Sun 11:00-19:00'),
    ('regent-street',   'Apple Regent Street',    'london',         'London',       'UK', 'W1B 5AH','235 Regent Street',            '+44 20 7153-9000','Mon-Sat 10:00-21:00, Sun 12:00-18:00'),
    ('covent-garden',   'Apple Covent Garden',    'london',         'London',       'UK', 'WC2E 8RA','1-7 The Piazza',              '+44 20 7447-1400','Mon-Sat 10:00-21:00, Sun 12:00-18:00'),
    ('marche-saint-germain','Apple Marche Saint-Germain','paris',   'Paris',        'FR', '75006', '12 Rue de Rennes',              '+33 1 84-79-1400','Mon-Sat 10:00-20:00, closed Sun'),
    ('omotesando',      'Apple Omotesando',       'tokyo',          'Tokyo',        'JP', '150-0001','4-2-13 Jingumae Shibuya',     '+81 3-6757-2700', 'Daily 10:00-21:00'),
    ('marina-bay-sands','Apple Marina Bay Sands', 'singapore',      'Singapore',    'SG', '018956','2 Bayfront Avenue B2-06',       '+65 6634-1900',   'Daily 10:00-22:00'),
    ('orchard-road',    'Apple Orchard Road',     'singapore',      'Singapore',    'SG', '238871','270 Orchard Road',              '+65 6604-1800',   'Daily 10:00-22:00'),
    ('hongkong-ifc',    'Apple ifc mall',         'hong-kong',      'Hong Kong',    'HK', '00000', 'L1 Shop 1018 ifc mall',         '+852 3971-3800',  'Daily 10:00-21:00'),
    ('shanghai-pudong', 'Apple Pudong',           'shanghai',       'Shanghai',     'CN', '200120','933 Lujiazui Ring Road',        '+86 21 6133-9900','Daily 10:00-22:00'),
]

def _store_by_slug(slug):
    return next((s for s in APPLE_RETAIL_STORES if s[0] == slug), None)


def _stores_by_city(city_slug):
    return [s for s in APPLE_RETAIL_STORES if s[2] == city_slug]


@app.route('/retail')
@app.route('/retail/')
def retail_index():
    """Apple Retail — list of every Apple Store, grouped by city."""
    by_city = {}
    for s in APPLE_RETAIL_STORES:
        by_city.setdefault((s[2], s[3], s[4]), []).append(s)
    page = {
        'title': 'Apple Store locations',
        'subtitle': f'{len(APPLE_RETAIL_STORES)} Apple Stores across the U.S. and around the world.',
        'body': [
            'Visit an Apple Store to shop the latest products, get expert help, book a Genius Bar appointment, or join a Today at Apple session.',
            'Trade in eligible devices for credit toward a new Apple product. Same-day pickup is available on most in-stock items.',
        ],
        'links': [
            ('In-store pickup', '/store/pickup'),
            ('Genius Bar', '/retail/the-grove/genius-bar'),
            ('Today at Apple', '/today'),
            ('Apple Trade In', '/trade-in'),
        ],
        'stores': APPLE_RETAIL_STORES,
        'by_city': by_city,
    }
    return render_template('info_page.html', topic='retail', page=page)


@app.route('/retail/<city_slug>')
@app.route('/retail/<city_slug>/')
def retail_city(city_slug):
    """Apple Retail — list of stores in a given city, or a specific store
    when the slug matches a store directly. Routes like
    `/retail/the-grove`, `/retail/los-angeles`, and `/retail/london` all
    work because store slugs and city slugs share the same namespace."""
    stores = _stores_by_city(city_slug)
    if not stores:
        # Maybe the slug is a store directly.
        store = _store_by_slug(city_slug)
        if store:
            return retail_store(city_slug)
        abort(404)
    city_label = stores[0][3]
    page = {
        'title': f'Apple Stores in {city_label}',
        'subtitle': f'{len(stores)} Apple Store location{"s" if len(stores) != 1 else ""} in {city_label}.',
        'body': [
            f'Shop, get expert help, and book Genius Bar appointments at one of {len(stores)} Apple locations in {city_label}.',
        ] + [f'{s[1]} — {s[6]}, {s[3]}, {s[4]} {s[5]}. Phone {s[7]}. Hours: {s[8]}.' for s in stores],
        'links': [(s[1], f'/retail/{s[0]}') for s in stores] +
                 [('Back to all Apple Stores', '/retail')],
    }
    return render_template('info_page.html', topic=f'retail/{city_slug}', page=page)


@app.route('/retail/<store_slug>/store')
def retail_store(store_slug):
    """Individual Apple Store landing page."""
    store = _store_by_slug(store_slug)
    if not store:
        abort(404)
    slug, name, city_slug, city, state, zipc, addr, phone, hours = store
    page = {
        'title': name,
        'subtitle': f'{addr}, {city}, {state} {zipc}',
        'body': [
            f'Hours: {hours}',
            f'Phone: {phone}',
            'Shop the latest iPhone, Mac, iPad, Apple Watch, AirPods, Apple Vision Pro, and accessories.',
            'Free Personal Setup with every purchase. Trade in eligible devices for credit toward your purchase.',
            'Same-day Apple Store Pickup available on most in-stock products — ready in as little as one hour.',
            'Specialist appointments available daily. Reserve a one-hour session online.',
        ],
        'links': [
            ('Book a Genius Bar appointment', f'/retail/{slug}/genius-bar'),
            ('Today at Apple sessions', f'/retail/{slug}/today-at-apple'),
            ('In-store pickup', f'/store/pickup?store={slug}'),
            ('Personal Setup', '#'),
            (f'All stores in {city}', f'/retail/{city_slug}'),
            ('All Apple Stores', '/retail'),
        ],
    }
    return render_template('info_page.html', topic=f'retail/{store_slug}', page=page)


@app.route('/retail/<store_slug>/genius-bar', methods=['GET', 'POST'])
def retail_genius_bar(store_slug):
    """Book a Genius Bar appointment at a specific Apple Store."""
    store = _store_by_slug(store_slug)
    if not store:
        abort(404)
    slug, name, _city_slug, city, state, zipc, addr, phone, hours = store
    submitted = (request.method == 'POST')
    requested_topic = request.values.get('topic', '').strip()
    requested_date = request.values.get('date', '').strip()
    body = [
        f'Genius Bar appointments at {name}.',
        f'Location: {addr}, {city}, {state} {zipc}.',
        f'Hours: {hours}.',
        'Bring your device, Apple ID password, and a photo ID. Appointments are 20 minutes by default; complex repairs may extend to 60 minutes.',
        'Common Genius Bar topics: iPhone repair, Mac diagnostic, Apple Watch battery service, AirPods replacement, Apple Vision Pro fit and Light Seal sizing.',
    ]
    if submitted:
        body = [f'Appointment requested — {name} — topic "{requested_topic or "General"}" on {requested_date or "next available"}.'] + body
    page = {
        'title': f'Genius Bar at {name}',
        'subtitle': 'Get hardware help from an Apple Expert.',
        'body': body,
        'links': [
            ('iPhone repair', f'/retail/{slug}/genius-bar?topic=iphone-repair'),
            ('Mac diagnostic', f'/retail/{slug}/genius-bar?topic=mac-diagnostic'),
            ('Apple Watch service', f'/retail/{slug}/genius-bar?topic=apple-watch-service'),
            ('AirPods service', f'/retail/{slug}/genius-bar?topic=airpods-service'),
            ('Vision Pro fit & Light Seal', f'/retail/{slug}/genius-bar?topic=vision-pro-fit'),
            ('Back to store', f'/retail/{slug}'),
        ],
    }
    return render_template('info_page.html', topic=f'retail/{store_slug}/genius-bar', page=page)


# ---------------------------------------------------------------------------
# Today at Apple — free in-store creative sessions across categories
# ---------------------------------------------------------------------------

TODAY_AT_APPLE_SESSIONS = [
    # (slug, title, category, duration_min, summary, body)
    ('photo-walks-skill-builders',         'Photo Walks: Skill Builders with iPhone',         'photography', 60,
     'Sharpen your eye with iPhone-led photo walks.',
     'Step outside the Apple Store with a Creative Pro to learn composition, lighting, and editing on iPhone 17 Pro. We provide gear; bring an open mind. Sessions every Saturday at participating stores.'),
    ('photo-portraits-with-iphone',        'Photo Lab: Portraits with iPhone',                'photography', 60,
     'Master the Portraits feature on iPhone.',
     'Learn the Portrait mode workflow on iPhone 17 — bokeh effects, lighting presets, depth control, and re-editing portraits after the shot in Photos.'),
    ('video-cinematic-on-iphone',          'Video Lab: Cinematic Mode and ProRes',            'video',       60,
     'Shoot beautifully shallow-focus videos on iPhone.',
     'A Creative Pro walks you through Cinematic mode, ProRes recording, Action mode, and editing in Final Cut Camera on iPhone.'),
    ('music-lab-garageband',               'Music Lab: Beats with GarageBand',                'music',       60,
     'Create your first beat in GarageBand on iPad.',
     'Pick up an iPad and a pair of AirPods and build a beat in GarageBand. Suitable for first-time musicians and producers.'),
    ('music-lab-logic-pro',                'Music Lab: Producing in Logic Pro',               'music',       90,
     'Mix and master in Logic Pro on MacBook Pro.',
     'Bring your tracks or use ours. Learn mixing, mastering, and Logic Pro for iPad workflows. Sessions are 90 minutes; prior GarageBand experience helps.'),
    ('art-and-design-procreate',           'Art and Design: Sketching in Procreate on iPad',  'art',         60,
     'Sketch and shade in Procreate with Apple Pencil Pro.',
     'A Creative Pro guides you through brushes, layers, and shading techniques in Procreate. Hands-on with Apple Pencil Pro.'),
    ('coding-club-swift-playgrounds',      'Coding Club: First Steps in Swift Playgrounds',   'coding',      60,
     'Write your first Swift app on iPad.',
     'Designed for ages 10+. Build a small app and run it on iPad. Counts toward Apple Schoolwork and Apple Teacher recognition.'),
    ('coding-lab-swiftui-mac',             'Coding Lab: Build a SwiftUI Layout on Mac',       'coding',      90,
     'Learn SwiftUI fundamentals with Xcode on Mac.',
     'A 90-minute hands-on lab. Bring a 13" or 15" MacBook Air (Mac mini provided at the store) and we will show how to build a list view in SwiftUI.'),
    ('apple-watch-walking-club',           'Apple Watch Walking Club',                        'fitness',     45,
     'Walk together — log your activity with Apple Watch.',
     'Group walk from the store using Apple Watch Workout app. Tips on goal setting, Activity rings, and pacing. Open to all fitness levels.'),
    ('today-at-apple-kids-hour',           'Today at Apple Kids Hour',                        'kids',        45,
     'Hands-on creative fun for ages 6 to 10.',
     'Stop-motion videos, sketching in Freeform, and short coding puzzles in Swift Playgrounds. Parent or guardian must attend.'),
    ('apple-pencil-handwriting',           'Apple Pencil Lab: Handwriting and Scribble',      'art',         45,
     'Practice Scribble and Markup on iPad Pro.',
     'Learn Apple Pencil Pro gestures, double-tap shortcuts, and the Scribble system that turns handwriting into text in any app.'),
    ('vision-pro-introductory-demo',       'Apple Vision Pro Introductory Demo',              'vision',      30,
     'Try Apple Vision Pro in store.',
     'A guided 30-minute demo of Apple Vision Pro. Try spatial photos and video, Mac Virtual Display, immersive Environments, and FaceTime with Persona. Available at most flagship stores; book in advance.'),
    ('accessibility-voiceover-discover',   'Accessibility Lab: Discover VoiceOver',           'accessibility',60,
     'Hands-on with the VoiceOver screen reader.',
     'Discover the VoiceOver Rotor, gestures, and Braille input. Suitable for anyone who is curious about Apple accessibility — including educators and family members.'),
    ('accessibility-personal-voice',       'Accessibility Lab: Set up Personal Voice',        'accessibility',60,
     'Create a Personal Voice on iPhone or iPad.',
     'Walk through the Personal Voice setup using 15 minutes of recorded prompts. Pair with Live Speech to type and have the device speak in your voice.'),
    ('skills-business-finder',             'Apple at Work: Build a Business Finder app',      'business',    90,
     'Build a small business finder with Numbers on Mac.',
     'A 90-minute lab building a customer list and chart in Numbers, then sharing as a Pages document. Ideal for small business owners.'),
]


@app.route('/today')
@app.route('/today/')
def today_at_apple_index():
    """Browse all Today at Apple sessions."""
    page = {
        'title': 'Today at Apple',
        'subtitle': f'{len(TODAY_AT_APPLE_SESSIONS)} free sessions covering photo, video, music, art, coding, fitness, and accessibility.',
        'body': [
            'Join free in-person sessions led by Apple Creative Pros. All gear is provided. Open to everyone.',
            'Most sessions run 45 to 90 minutes. Some sessions are designed for ages 6-10, marked Kids Hour.',
        ],
        'links': [(s[1], f'/today/{s[0]}') for s in TODAY_AT_APPLE_SESSIONS],
        'sessions': TODAY_AT_APPLE_SESSIONS,
    }
    return render_template('info_page.html', topic='today', page=page)


@app.route('/today/<session_slug>', methods=['GET', 'POST'])
def today_at_apple_session(session_slug):
    session_data = next((s for s in TODAY_AT_APPLE_SESSIONS if s[0] == session_slug), None)
    if not session_data:
        abort(404)
    slug, title, cat, duration, summary, body_text = session_data
    submitted = (request.method == 'POST')
    requested_store = request.values.get('store', '').strip()
    requested_date = request.values.get('date', '').strip()
    body = [summary, body_text,
            f'Duration: {duration} minutes.',
            f'Category: {cat.capitalize()}.',
            'All Apple devices are provided — bring yourself, your curiosity, and a friend.']
    if submitted:
        body = [f'Booked — {title} at "{requested_store or "your selected store"}" on {requested_date or "next available date"}.'] + body
    page = {
        'title': title,
        'subtitle': summary,
        'body': body,
        'links': [(s[1], f'/retail/{s[0]}/today-at-apple') for s in APPLE_RETAIL_STORES[:6]] +
                 [('All Today at Apple sessions', '/today')],
    }
    return render_template('info_page.html', topic=f'today/{slug}', page=page)


@app.route('/retail/<store_slug>/today-at-apple')
def retail_today(store_slug):
    """Today at Apple schedule at a specific Apple Store."""
    store = _store_by_slug(store_slug)
    if not store:
        abort(404)
    page = {
        'title': f'Today at Apple at {store[1]}',
        'subtitle': f'Free creative sessions at {store[1]}.',
        'body': [
            'Browse all upcoming Today at Apple sessions at this location. Sessions are first-come, first-served when seats remain on the day; reservations recommended.',
            'Sessions vary by store. The full Today at Apple catalog runs nightly worldwide.',
        ],
        'links': [(t[1], f'/today/{t[0]}?store={store_slug}') for t in TODAY_AT_APPLE_SESSIONS] +
                 [('Back to store', f'/retail/{store_slug}')],
    }
    return render_template('info_page.html', topic=f'retail/{store_slug}/today-at-apple', page=page)


# ---------------------------------------------------------------------------
# Refurbished store — filtered shop view (no DB change)
# ---------------------------------------------------------------------------

@app.route('/shop/refurbished')
@app.route('/shop/refurbished/')
def shop_refurbished():
    """Apple Certified Refurbished — listing of every refurbished SKU."""
    cat = request.args.get('category', '').strip().lower()
    q = Product.query.filter(Product.subcategory == 'refurbished')
    if cat:
        q = q.filter(Product.category == cat)
    products = q.order_by(Product.price.desc()).all()
    page = {
        'title': 'Apple Certified Refurbished',
        'subtitle': f'{len(products)} Apple-tested refurbished products.',
        'body': [
            'Apple Certified Refurbished products are fully tested, repackaged, and covered by a one-year Apple limited warranty. AppleCare+ is available for an additional fee.',
            'Refurbished products are typically discounted 15% off the equivalent new price. Free shipping and 14-day returns on every order.',
        ],
        'links': [(p.name, f'/shop/refurbished/{p.slug.replace("certified-refurbished-", "")}') for p in products[:60]] +
                 [('Refurbished iPhone', '/shop/refurbished?category=iphone'),
                  ('Refurbished Mac', '/shop/refurbished?category=mac'),
                  ('Refurbished iPad', '/shop/refurbished?category=ipad'),
                  ('Refurbished Apple Watch', '/shop/refurbished?category=watch'),
                  ('Refurbished AirPods', '/shop/refurbished?category=airpods')],
        'products': products,
    }
    return render_template('info_page.html', topic='shop/refurbished', page=page)


@app.route('/shop/refurbished/<slug>')
def shop_refurbished_product(slug):
    """Single refurbished product detail (redirects to canonical product page)."""
    p = (Product.query.filter_by(slug=f'certified-refurbished-{slug}').first()
         or Product.query.filter_by(slug=slug).first())
    if not p:
        abort(404)
    return redirect(url_for('product_detail', slug=p.slug))


# ---------------------------------------------------------------------------
# Accessibility — per-feature drilldown
# ---------------------------------------------------------------------------

ACCESSIBILITY_FEATURES = {
    'vision': {
        'title': 'Vision Accessibility',
        'subtitle': 'See more, read more, work more — at your own pace.',
        'body': [
            'VoiceOver — built-in screen reader that describes what is on the display and lets you control iPhone, iPad, Mac, Apple Watch, and Apple TV with gestures or a refreshable Braille display.',
            'Zoom — magnify anywhere on screen up to 15×, with a picture-in-picture window so the rest of the display stays in context.',
            'Magnifier — turn iPhone into a digital magnifying glass with point-and-shoot detection for People, Doors, and Furniture.',
            'Display & Text Size — adjust contrast, color filters, reduce motion, and use Bold Text app-wide.',
            'Spoken Content and Live Speech — have any text spoken aloud, or type and have Apple devices speak in a Personal Voice.',
        ],
        'links': [
            ('Set up VoiceOver', '/support/article/accessibility-features'),
            ('Use Magnifier', '/support/article/accessibility-features'),
            ('Apple Vision Pro and accessibility', '/vision-pro'),
            ('All accessibility features', '/accessibility'),
        ],
    },
    'hearing': {
        'title': 'Hearing Accessibility',
        'subtitle': 'Hear more, communicate more.',
        'body': [
            'Made for iPhone Hearing Aids — stream audio, take calls, and adjust hearing aid settings directly from iPhone.',
            'Live Captions — automatic real-time captions for any FaceTime call, phone call, or audio playing on your device.',
            'Sound Recognition — be alerted on iPhone, iPad, Apple Watch, or HomePod when smoke alarms, sirens, doorbells, or a baby cry are detected nearby.',
            'AirPods Pro Hearing Aid Feature — clinical-grade hearing aid functionality powered by AirPods Pro 2 with the H2 chip (US, AU, EU).',
            'RTT and TTY support — send and receive real-time text over a cellular connection on iPhone.',
        ],
        'links': [
            ('AirPods Pro Hearing Aid feature', '/product/airpods-pro-3'),
            ('Live Captions setup', '/support/article/accessibility-features'),
            ('Made for iPhone hearing aids', '/accessibility'),
            ('All accessibility features', '/accessibility'),
        ],
    },
    'mobility': {
        'title': 'Mobility Accessibility',
        'subtitle': 'Control devices the way that works for you.',
        'body': [
            'AssistiveTouch — replace multi-finger gestures with single-tap actions, and use Apple Watch to control your devices via wrist motion.',
            'Voice Control — navigate and edit on iPhone, iPad, and Mac entirely by voice, with a full grid overlay for precision.',
            'Switch Control — drive iPhone, iPad, and Mac with one or more external switches, head gestures, or facial expressions.',
            'Eye Tracking — control iPhone and iPad using only your eyes, calibrated in seconds with the front camera (iPadOS / iOS 18 and later).',
            'Back Tap and Action Button — assign actions to a back-of-iPhone tap or the Action button on iPhone Pro models.',
        ],
        'links': [
            ('AssistiveTouch setup', '/support/article/accessibility-features'),
            ('Voice Control', '/support/article/accessibility-features'),
            ('Switch Control accessories', '/product/switch-control-jelly-bean-switch'),
            ('All accessibility features', '/accessibility'),
        ],
    },
    'speech': {
        'title': 'Speech Accessibility',
        'subtitle': 'Type to talk. Save your voice.',
        'body': [
            'Live Speech — type what you want to say and have iPhone, iPad, Mac, or Apple Watch speak it aloud during in-person and FaceTime conversations.',
            'Personal Voice — record about 15 minutes of audio on iPhone or iPad and create a synthesized version of your own voice for use with Live Speech.',
            'Vocal Shortcuts — train Siri to recognize custom utterances and run Shortcuts hands-free.',
        ],
        'links': [
            ('Set up Personal Voice', '/today/accessibility-personal-voice'),
            ('Live Speech', '/support/article/accessibility-features'),
            ('All accessibility features', '/accessibility'),
        ],
    },
    'cognitive': {
        'title': 'Cognitive Accessibility',
        'subtitle': 'A simpler way to use Apple devices.',
        'body': [
            'Assistive Access — a distilled experience of iPhone and iPad with high-contrast buttons, larger text, and a focused set of apps.',
            'Guided Access — temporarily restrict iPhone or iPad to a single app, with controls to disable touch areas or hardware buttons.',
            'Background Sounds — generate balanced noise, ocean, rain, or stream to help minimize distractions or aid focus and rest.',
            'Personal Voice — speech tools designed for users with progressive speech conditions.',
        ],
        'links': [
            ('Set up Assistive Access', '/support/article/accessibility-features'),
            ('Background Sounds', '/support/article/accessibility-features'),
            ('All accessibility features', '/accessibility'),
        ],
    },
}


@app.route('/accessibility/<feature>')
@app.route('/accessibility/<feature>/')
def accessibility_feature(feature):
    page = ACCESSIBILITY_FEATURES.get((feature or '').lower())
    if not page:
        abort(404)
    return render_template('info_page.html', topic=f'accessibility/{feature}', page=page)


@app.route('/accessibility/feature/<feature>')
def accessibility_feature_alias(feature):
    return redirect(url_for('accessibility_feature', feature=feature), code=301)


# ---------------------------------------------------------------------------
# Education / Business — R4 add-on flows
# ---------------------------------------------------------------------------

@app.route('/education-pricing/eligibility')
@app.route('/education-pricing/eligibility/')
def education_eligibility():
    """Eligibility check for Apple Education Pricing (UNiDAYS-verified)."""
    page = {
        'title': 'Apple Education Pricing — Eligibility',
        'subtitle': 'Verify your status with UNiDAYS to unlock savings.',
        'body': [
            'You are eligible for Apple Education Pricing if you are a current or newly accepted college student.',
            'Parents buying for a college student in their household are also eligible.',
            'Teachers and staff at all grade levels — primary, secondary, and post-secondary — qualify year-round.',
            'Homeschool teachers, board members, and PTA officers also qualify when buying for use with students.',
            'Verification is handled at checkout by UNiDAYS. Your status is reverified once per year; no manual paperwork required.',
        ],
        'links': [
            ('Shop Mac with Education savings', '/mac'),
            ('Shop iPad with Education savings', '/ipad'),
            ('Shop AppleCare+ for Education', '/product/education-savings-applecare-edu-macbook-pro-14'),
            ('Back to Education Pricing', '/education-pricing'),
        ],
    }
    return render_template('info_page.html', topic='education-pricing/eligibility', page=page)


@app.route('/business/quote/bulk', methods=['GET', 'POST'])
def business_quote_bulk():
    """Apple at Work — bulk quote request (10+ units)."""
    submitted = (request.method == 'POST')
    page = {
        'title': 'Bulk Business Quote',
        'subtitle': 'For orders of 10 or more devices.',
        'body': [
            'For organizations purchasing 10 or more Macs, iPads, or iPhones, request a bulk quote from an Apple Business Specialist.',
            'Bulk quotes include volume pricing, Apple Financial Services lease options, zero-touch deployment with Apple Business Manager, and AppleCare+ for Business coverage.',
            'For the U.S. business team, call 1-800-854-3680 Monday through Friday, 7 AM – 5 PM PT.',
        ] + ([f'Quote received. An Apple Business Specialist will follow up within one business day.'] if submitted else []),
        'links': [
            ('Volume Bundle: 10× MacBook Air 13"', '/product/volume-bundle-macbook-air-13-10pk'),
            ('Volume Bundle: 25× MacBook Air 13"', '/product/volume-bundle-macbook-air-13-25pk'),
            ('Volume Bundle: 25× iPad Air M4',     '/product/volume-bundle-ipad-air-m4-25pk'),
            ('Volume Bundle: 50× iPhone 16',       '/product/volume-bundle-iphone-16-50pk'),
            ('Apple Business Essentials', '/product/apple-business-essentials-25-seat'),
            ('Back to Apple at Work', '/business'),
        ],
    }
    return render_template('info_page.html', topic='business/quote/bulk', page=page)


# ---------------------------------------------------------------------------

@app.route('/configure/<slug>')
def configurator(slug):
    product = Product.query.filter_by(slug=slug).first_or_404()
    return render_template('configurator.html', product=product,
                           upgrades=product.get_config_upgrades(),
                           keyboards=product.get_keyboard_options())


@app.route('/compare/<category>')
@app.route('/compare/<category>/')
def compare(category):
    """Side-by-side spec comparison page for every product in a category."""
    category = (category or '').lower()
    # canonical title + upstream category slug
    titles = {
        'mac': 'Mac', 'iphone': 'iPhone', 'ipad': 'iPad',
        'watch': 'Apple Watch', 'airpods': 'AirPods',
        'accessories': 'Accessories', 'vision': 'Apple Vision Pro',
    }
    title = titles.get(category, category.capitalize())
    products = Product.query.filter_by(category=category).order_by(Product.price.desc()).all()
    return render_template('compare.html', products=products,
                           category=category, title=title)


# ---------------------------------------------------------------------------
# API - Product data (for JS interactions)
# ---------------------------------------------------------------------------

@app.route('/api/products/<category>')
def api_products(category):
    products = Product.query.filter_by(category=category).all()
    return jsonify([{
        'id': p.id, 'name': p.name, 'slug': p.slug, 'price': p.price,
        'subtitle': p.subtitle, 'image': p.image, 'is_new': p.is_new,
        'colors': p.get_colors(), 'monthly_price': p.monthly_price,
    } for p in products])


# ---------------------------------------------------------------------------
# R5 — trade-in IMEI lookup
# ---------------------------------------------------------------------------

# Deterministic lookup by IMEI/serial — derives device + condition from the
# checksum of the IMEI string so that the same IMEI always returns the same
# answer (byte-id reset safe).
TRADEIN_IMEI_TABLE = {
    # canonical sample IMEIs that benchmarks can hard-code
    '353299814617852': ('iPhone 13',              'good',      240.00),
    '356789012345678': ('iPhone 14',              'good',      340.00),
    '358901234567890': ('iPhone 15',              'excellent', 470.00),
    '351234567890123': ('iPhone 15 Pro',          'excellent', 650.00),
    '352345678901234': ('iPhone 16',              'good',      540.00),
    '353456789012345': ('iPhone 16 Pro',          'excellent', 720.00),
    '354567890123456': ('iPhone 16 Pro Max',      'excellent', 840.00),
    '355678901234567': ('iPhone 17',              'good',      640.00),
    '356678901234567': ('iPhone 17 Pro',          'excellent', 820.00),
    '357678901234567': ('iPhone 17 Pro Max',      'excellent', 940.00),
    'C02ZL0VKLVDR':    ('MacBook Air M2',         'good',      430.00),
    'C02ZL0VKLVDQ':    ('MacBook Pro M3',         'good',      900.00),
    'WW9G2LL/A':       ('Apple Watch Ultra 2',    'good',      280.00),
    'F2LWG4LD92':      ('iPad Pro M2 11-inch',    'good',      410.00),
}


@app.route('/trade-in/imei', methods=['GET', 'POST'])
@csrf.exempt
def trade_in_imei():
    """Trade-in by IMEI/serial number lookup.

    R5 — Adds an instant-credit lookup flow. POST {imei, condition?} returns
    the recognized device + an Apple Gift Card / instant-credit estimate.
    GET renders an explanatory page with sample IMEIs.
    """
    imei = (request.values.get('imei') or '').strip().upper()
    condition = (request.values.get('condition') or 'good').strip().lower()
    if request.method == 'POST' and imei:
        # 1) Exact-match table.
        match = TRADEIN_IMEI_TABLE.get(imei)
        if not match:
            # 2) Fuzzy match — hash the IMEI to a stable bucket, fall through
            # to whichever TradeInValue row has the closest device tier.
            import hashlib
            h = int.from_bytes(hashlib.md5(imei.encode()).digest()[:4], 'big')
            rows = TradeInValue.query.all()
            if rows:
                row = rows[h % len(rows)]
                match = (row.device, condition, float(row.value))
        if match:
            device, _cond, base_value = match
            mult = {'excellent': 1.05, 'good': 1.0, 'fair': 0.7, 'broken': 0.3}.get(condition, 1.0)
            quoted = round(float(base_value) * mult, 2)
            return jsonify({
                'eligible': True,
                'imei': imei,
                'device_matched': device,
                'condition': condition,
                'estimated_value_usd': quoted,
                'max_value_usd': float(base_value),
                'instant_credit': True,
                'delivery': 'Apple Gift Card via email within 24 hours',
                'next_step_url': f'/trade-in/quote?device={device}&condition={condition}',
            }), 200
        return jsonify({
            'eligible': False, 'imei': imei,
            'message': 'IMEI not recognized. Verify the 15-digit IMEI on your device under Settings > General > About.',
        }), 200

    # GET → explanatory page with sample IMEIs the agent can use.
    page = {
        'title': 'Trade In — IMEI Lookup',
        'subtitle': 'Look up your trade-in credit with your IMEI or serial number.',
        'body': [
            'On iPhone, dial *#06# or open Settings > General > About to find your 15-digit IMEI.',
            'On Mac, open Apple menu > About This Mac to find your serial number.',
            'On Apple Watch, open the Watch app > General > About on your paired iPhone.',
            'Submit your IMEI/serial below to receive an instant trade-in credit estimate. '
            'Credit is delivered as an Apple Gift Card via email within 24 hours.',
            'Sample IMEIs you can try: 353299814617852 (iPhone 13), 356789012345678 (iPhone 14), '
            '358901234567890 (iPhone 15).',
        ],
        'links': [
            ('Look up another device', '/trade-in'),
            ('Trade-in promos', '/shop?category=accessories'),
            ('Apple Trade In FAQ', '/support/article/apple-trade-in'),
        ],
    }
    return render_template('info_page.html', topic='trade-in/imei', page=page)


# ---------------------------------------------------------------------------
# R5 — AppleCare coverage check by serial / IMEI
# ---------------------------------------------------------------------------

# Deterministic AppleCare coverage table. Each serial returns a stable result.
APPLECARE_COVERAGE_TABLE = {
    'C02ZL0VKLVDR': ('MacBook Air M2',     'AppleCare+',          '2026-08-12', True),
    'C02ZL0VKLVDQ': ('MacBook Pro M3',     'AppleCare+',          '2027-02-04', True),
    'WW9G2LL/A':    ('Apple Watch Ultra 2','AppleCare+',          '2026-11-30', True),
    'F2LWG4LD92':   ('iPad Pro M2 11-inch','Apple Limited Warranty','2025-06-15', False),
    '353299814617852': ('iPhone 13',       'AppleCare+ with Theft and Loss', '2025-11-15', True),
    '358901234567890': ('iPhone 15',       'AppleCare+',          '2026-09-12', True),
    '356678901234567': ('iPhone 17 Pro',   'AppleCare+ with Theft and Loss', '2027-09-22', True),
    'XGD2Y0J6Z9':      ('Apple Vision Pro','AppleCare+',          '2026-02-02', True),
    'AB1234CDEFGH':    ('AirPods Pro 3',   'No Coverage',         '',            False),
}


@app.route('/applecare/coverage', methods=['GET', 'POST'])
@csrf.exempt
def applecare_coverage():
    """AppleCare coverage lookup by serial number or IMEI.

    R5 — Returns AppleCare+ tier, expiration date, and Theft & Loss status.
    """
    sn = (request.values.get('serial') or request.values.get('imei') or '').strip().upper()
    if request.method == 'POST' and sn:
        info = APPLECARE_COVERAGE_TABLE.get(sn)
        if not info:
            # Deterministic fallback so multi-step agents always make progress.
            import hashlib
            h = int.from_bytes(hashlib.md5(sn.encode()).digest()[:4], 'big')
            tiers = list(APPLECARE_COVERAGE_TABLE.values())
            info = tiers[h % len(tiers)]
        device, tier, expiry, theft = info
        return jsonify({
            'serial_or_imei': sn,
            'device': device,
            'coverage_tier': tier,
            'expiration_date': expiry,
            'theft_and_loss': theft,
            'covered': tier != 'No Coverage',
            'support_phone': '1-800-275-2273',
            'manage_url': '/applecare/manage',
        }), 200

    page = {
        'title': 'AppleCare+ Coverage Check',
        'subtitle': 'Look up your AppleCare+ coverage by serial or IMEI.',
        'body': [
            'Enter the serial number (Mac, iPad, AirPods) or IMEI (iPhone, Cellular iPad, Apple Watch) of your Apple device.',
            'AppleCare+ covers unlimited incidents of accidental damage and priority 24/7 access to Apple Specialists.',
            'AppleCare+ with Theft and Loss is available for iPhone — adds coverage for up to two theft/loss incidents per term.',
            'Sample serials you can try: C02ZL0VKLVDR (MacBook Air M2), WW9G2LL/A (Apple Watch Ultra 2), '
            'F2LWG4LD92 (iPad Pro M2 11-inch).',
        ],
        'links': [
            ('Shop AppleCare+', '/applecare'),
            ('Compare AppleCare plans', '/applecare-compare'),
            ('Support phone: 1-800-275-2273', 'tel:18002752273'),
        ],
    }
    return render_template('info_page.html', topic='applecare/coverage', page=page)


# ---------------------------------------------------------------------------
# R5 — Repair status tracker
# ---------------------------------------------------------------------------

REPAIR_STATUS_TABLE = {
    'R12345678': ('iPhone 17 Pro display replacement', 'In transit — return shipment',  '2026-05-28', 'Apple Service Center Memphis'),
    'R12345679': ('MacBook Pro 14 battery service',    'Diagnostic complete',           '2026-05-30', 'Apple Service Center Elk Grove'),
    'R12345680': ('Apple Watch Ultra 2 crown service', 'Pending part — backorder',      '2026-06-05', 'Apple Service Center Memphis'),
    'R12345681': ('AirPods Pro 3 left bud replacement','Delivered',                     '2026-05-22', 'You'),
    'R12345682': ('iPad Pro M4 screen replacement',    'In repair',                     '2026-05-29', 'Apple Service Center Elk Grove'),
    'R12345683': ('iPhone 16 battery replacement',     'Awaiting customer drop-off',    '2026-05-26', 'Apple The Grove'),
    'R12345684': ('Vision Pro Light Seal swap',        'Repair complete — ready for pickup','2026-05-25', 'Apple Fifth Avenue'),
    'R12345685': ('Mac mini logic board replacement',  'Quote sent — awaiting approval', '2026-05-24', 'Apple Service Center Memphis'),
    'R12345686': ('Apple Watch SE 2 strap exchange',   'Delivered',                     '2026-05-20', 'You'),
    'R12345687': ('iPhone 15 Pro Max camera repair',   'In transit — outbound to customer','2026-05-27', 'Apple Service Center Memphis'),
}


@app.route('/repair/status', methods=['GET', 'POST'])
@csrf.exempt
def repair_status():
    """Repair status tracker. POST {repair_id} → JSON status."""
    rid = (request.values.get('repair_id') or '').strip().upper()
    if request.method == 'POST' and rid:
        info = REPAIR_STATUS_TABLE.get(rid)
        if not info:
            import hashlib
            h = int.from_bytes(hashlib.md5(rid.encode()).digest()[:4], 'big')
            rows = list(REPAIR_STATUS_TABLE.values())
            info = rows[h % len(rows)]
        repair, status, eta, location = info
        return jsonify({
            'repair_id': rid,
            'repair': repair,
            'status': status,
            'estimated_completion': eta,
            'current_location': location,
            'support_phone': '1-800-275-2273',
        }), 200

    page = {
        'title': 'Repair Status',
        'subtitle': 'Track your Apple repair.',
        'body': [
            'Enter the repair ID from your service confirmation email (starts with R followed by 8 digits).',
            'Repair status is updated multiple times per day as your device moves through the Apple Service network.',
            'For urgent help, call 1-800-275-2273 or chat with an Apple Specialist.',
            'Sample repair IDs you can try: R12345678 (iPhone 17 Pro display), R12345679 (MacBook Pro 14 battery), '
            'R12345680 (Apple Watch Ultra 2 crown).',
        ],
        'links': [
            ('Self Service Repair', '/support/repair'),
            ('Genius Bar booking', '/retail'),
            ('Apple Service Center info', '/support'),
        ],
    }
    return render_template('info_page.html', topic='repair/status', page=page)


# ---------------------------------------------------------------------------
# R5 — Apple Card application + Apple Wallet add-pass + Find My + Family Sharing
# ---------------------------------------------------------------------------

@app.route('/apple-card', methods=['GET', 'POST'])
@csrf.exempt
def apple_card_application():
    """Apple Card application form. POST {full_name, ssn_last4, dob, income, ...} → decision."""
    if request.method == 'POST':
        full_name = (request.values.get('full_name') or '').strip()
        income = request.values.get('annual_income', '').strip()
        ssn_last4 = (request.values.get('ssn_last4') or '').strip()
        if not full_name or not ssn_last4:
            return jsonify({'approved': False, 'error': 'full_name and ssn_last4 required'}), 400
        # Deterministic decision: hash the SSN last4 to decide approval + line.
        import hashlib
        h = int.from_bytes(hashlib.md5(ssn_last4.encode()).digest()[:4], 'big')
        approved = (h % 10) != 0  # 9/10 approved
        line = 1000 + (h % 25) * 1000  # $1000 - $25000
        apr_low = 19.24 + (h % 6) * 0.5
        return jsonify({
            'approved': approved,
            'applicant': full_name,
            'credit_line_usd': float(line) if approved else 0.0,
            'apr_range': f'{apr_low:.2f}% – {apr_low+9.74:.2f}% variable',
            'daily_cash': '3% at Apple, 2% via Apple Pay, 1% on titanium card',
            'titanium_card_arrival_days': 7 if approved else 0,
            'wallet_add_url': '/wallet/add?pass=apple-card' if approved else None,
            'message': ('Approved — your virtual Apple Card is now in Apple Wallet. Titanium card ships in 7 days.'
                        if approved
                        else 'Application requires manual review. A Goldman Sachs specialist will call you within 3 business days.'),
        }), 200

    page = {
        'title': 'Apple Card',
        'subtitle': 'Apply for Apple Card with Goldman Sachs.',
        'body': [
            'Apple Card is built into the Wallet app on iPhone. Apply in minutes with no impact to your credit score.',
            'Earn 3% Daily Cash at Apple, 2% with Apple Pay, and 1% on titanium card purchases.',
            'No fees — no annual, no foreign transaction, no late fees, ever.',
            'Add to Apple Wallet instantly upon approval. Titanium card arrives in 7 days.',
            'POST to /apple-card with full_name + ssn_last4 + annual_income to apply.',
        ],
        'links': [
            ('Apple Card welcome materials', '/product/wallet-r5-apple-card-welcome'),
            ('Daily Cash boost partners', '/product/wallet-r5-apple-card-daily-cash'),
            ('Add to Wallet', '/wallet/add?pass=apple-card'),
        ],
    }
    return render_template('info_page.html', topic='apple-card', page=page)


@app.route('/wallet/add', methods=['GET', 'POST'])
@csrf.exempt
def wallet_add():
    """Add a pass to Apple Wallet. GET shows wallet contents; POST adds a pass."""
    pass_type = (request.values.get('pass') or '').strip().lower()
    if request.method == 'POST' and pass_type:
        # Deterministic pass ID derived from pass type.
        import hashlib
        pid = 'pkpass-' + hashlib.md5(pass_type.encode()).hexdigest()[:12]
        return jsonify({
            'added': True,
            'pass_type': pass_type,
            'pass_id': pid,
            'wallet_url': f'/wallet/pass/{pid}',
            'message': f'Added {pass_type} to Apple Wallet.',
        }), 200

    page = {
        'title': 'Apple Wallet',
        'subtitle': 'Add passes, keys, and cards to Apple Wallet.',
        'body': [
            'Apple Wallet stores your credit and debit cards, transit cards, boarding passes, event tickets, '
            'hotel keys, car keys, and more — all in one place.',
            'POST to /wallet/add with ?pass=<type> to add a pass. Supported pass types include apple-card, '
            'boarding-pass, hotel-key, car-key, transit-card, event-ticket, loyalty-card, student-id.',
            'Hotel keys are now supported at 60+ hotel chains. Tap your iPhone or Apple Watch on the door to unlock.',
            'Car keys are supported on BMW, Hyundai, Kia, Genesis, and Acura. Use Apple Watch to unlock — no need to take out iPhone.',
        ],
        'links': [
            ('Add Apple Card', '/wallet/add?pass=apple-card'),
            ('Add Hotel Key (sample)', '/wallet/add?pass=hotel-key'),
            ('Add Boarding Pass (sample)', '/wallet/add?pass=boarding-pass'),
            ('Add Car Key (sample)', '/wallet/add?pass=car-key'),
            ('Add Transit Card (sample)', '/wallet/add?pass=transit-card'),
        ],
    }
    return render_template('info_page.html', topic='wallet', page=page)


@app.route('/wallet/pass/<pass_id>')
def wallet_pass_view(pass_id):
    """Show a single Wallet pass by ID. Used as post-add landing page."""
    page = {
        'title': f'Wallet Pass {pass_id}',
        'subtitle': f'Pass ID: {pass_id}',
        'body': [
            'This pass is now stored in Apple Wallet on iPhone and synced to Apple Watch.',
            'Tap the pass in Wallet to view details, share, or remove.',
            'Hotel and event passes may surface notifications on the Lock Screen before your appointment time.',
        ],
        'links': [
            ('Back to Wallet', '/wallet/add'),
            ('Wallet help', '/support/article/apple-wallet-help'),
        ],
    }
    return render_template('info_page.html', topic=f'wallet/pass/{pass_id}', page=page)


@app.route('/find-my/locate-airtag', methods=['GET', 'POST'])
@csrf.exempt
def find_my_locate_airtag():
    """Find My — locate an AirTag by serial. Returns the last seen location."""
    serial = (request.values.get('serial') or '').strip().upper()
    if request.method == 'POST' and serial:
        # Deterministic location lookup.
        import hashlib
        h = int.from_bytes(hashlib.md5(serial.encode()).digest()[:4], 'big')
        sample_locations = [
            ('Apple The Grove', 34.0726, -118.3568, '189 The Grove Drive, Los Angeles, CA'),
            ('Apple Fifth Avenue', 40.7637, -73.9728, '767 5th Ave, New York, NY'),
            ('Apple Park', 37.3346, -122.0090, 'Apple Park Visitor Center, Cupertino, CA'),
            ('Apple Regent Street', 51.5125, -0.1411, '235 Regent St, London, UK'),
            ('Apple Omotesando', 35.6663, 139.7126, '4-2-13 Jingumae, Shibuya-ku, Tokyo'),
            ('Home — 742 Market St, San Francisco', 37.7857, -122.4011, '742 Market Street, San Francisco, CA'),
        ]
        loc_name, lat, lng, addr = sample_locations[h % len(sample_locations)]
        from datetime import timedelta
        last_seen = (MIRROR_REFERENCE_DATE - timedelta(hours=h % 48)).isoformat()
        return jsonify({
            'serial': serial,
            'found': True,
            'last_seen_at': last_seen,
            'location_name': loc_name,
            'address': addr,
            'lat': lat, 'lng': lng,
            'play_sound_url': f'/find-my/play-sound?serial={serial}',
            'lost_mode_url': f'/find-my/lost-mode?serial={serial}',
        }), 200

    page = {
        'title': 'Find My — Locate AirTag',
        'subtitle': 'Locate any AirTag on the Find My network.',
        'body': [
            'The Find My network uses hundreds of millions of Apple devices to anonymously help locate your AirTag.',
            'POST to /find-my/locate-airtag with ?serial=<airtag-serial> to retrieve the last known location.',
            'Use Precision Finding on iPhone 11 and later to home in on a nearby AirTag with on-screen directions.',
            'Sample serials: AT001234567890, AT001234567891, AT001234567892.',
        ],
        'links': [
            ('Shop AirTag', '/product/airtag'),
            ('Shop AirTag 4-pack', '/product/airtag-4-pack'),
            ('Find My on Apple devices', '/find-my'),
        ],
    }
    return render_template('info_page.html', topic='find-my/locate-airtag', page=page)


# In-memory family roster (deterministic, reset on rebuild).
FAMILY_SHARING_ROSTER = {
    'alice.j@test.com': ['bob.c@test.com', 'carol.d@test.com'],
    'bob.c@test.com':   ['david.k@test.com'],
    'carol.d@test.com': [],
    'david.k@test.com': [],
}


@app.route('/family-sharing/add-member', methods=['GET', 'POST'])
@csrf.exempt
def family_sharing_add_member():
    """Add a member to Family Sharing. POST {organizer, member_email} → status."""
    if request.method == 'POST':
        organizer = (request.values.get('organizer') or '').strip().lower()
        member = (request.values.get('member_email') or '').strip().lower()
        if not organizer or not member:
            return jsonify({'added': False, 'error': 'organizer and member_email required'}), 400
        roster = FAMILY_SHARING_ROSTER.get(organizer, [])
        if len(roster) >= 5:
            return jsonify({'added': False, 'error': 'Family Sharing maximum of 6 members reached'}), 400
        if member in roster:
            return jsonify({'added': False, 'error': 'Member already in family'}), 400
        # Deterministic: do not persist (rebuild resets), but echo state.
        new_roster = list(roster) + [member]
        return jsonify({
            'added': True,
            'organizer': organizer,
            'member_email': member,
            'family_size': len(new_roster) + 1,
            'family_roster': [organizer] + new_roster,
            'invite_sent': True,
            'ask_to_buy_default': True,
            'shared_subscriptions': ['Apple One Family', 'iCloud+ 2TB', 'Apple Music Family'],
        }), 200

    page = {
        'title': 'Family Sharing — Add Member',
        'subtitle': 'Invite up to 5 other family members to share Apple subscriptions, purchases, and iCloud+ storage.',
        'body': [
            'Family Sharing lets up to 6 people in your household share App Store purchases, Apple subscriptions, '
            'iCloud+ storage, and an Apple Music family plan — without sharing accounts.',
            'POST to /family-sharing/add-member with organizer (your Apple ID) + member_email (their Apple ID).',
            'Members under 13 get an Ask to Buy default that requires a parent or guardian to approve purchases.',
            'Sample organizers: alice.j@test.com (current family size 3), bob.c@test.com (current family size 2).',
        ],
        'links': [
            ('Family Sharing setup', '/family-sharing'),
            ('Family Sharing — Find My Family', '/product/family-r5-family-sharing-find-my'),
            ('Apple One Family', '/product/apple-one-family'),
        ],
    }
    return render_template('info_page.html', topic='family-sharing/add-member', page=page)


# ---------------------------------------------------------------------------
# R5 — AJAX shipping estimate by ZIP code
# ---------------------------------------------------------------------------

@app.route('/api/shipping/estimate', methods=['GET', 'POST'])
@csrf.exempt
def shipping_estimate():
    """Return shipping cost + ETA for a given ZIP code. Used by the AJAX
    enhancement on /shop/bag and /checkout."""
    zip_code = (request.values.get('zip') or '').strip()
    method = (request.values.get('method') or 'standard').strip().lower()
    if not zip_code or not zip_code.isdigit() or len(zip_code) != 5:
        return jsonify({'error': 'valid 5-digit ZIP required'}), 400
    # Deterministic ETA based on zip first digit.
    fd = int(zip_code[0])
    # 0/1 = Northeast, 2/3 = Mid-Atl/South, 4/5/6 = Midwest, 7 = TX/OK,
    # 8 = Mountain, 9 = West coast. Apple ships from Reno NV — west is fast.
    eta_days_std = [4, 4, 5, 5, 4, 4, 3, 4, 2, 1][fd]
    eta_days_express = max(1, eta_days_std - 2)
    method_costs = {
        'standard': (0.00, eta_days_std),
        'express':  (9.99, eta_days_express),
        'overnight':(19.99, 1),
    }
    cost, eta = method_costs.get(method, method_costs['standard'])
    return jsonify({
        'zip': zip_code,
        'method': method,
        'cost_usd': cost,
        'estimated_delivery_days': eta,
        'delivery_date_estimate': (MIRROR_REFERENCE_DATE + __import__('datetime').timedelta(days=eta)).date().isoformat(),
        'all_methods': [
            {'method': k, 'cost_usd': v[0], 'eta_days': v[1]} for k, v in method_costs.items()
        ],
    }), 200


# ---------------------------------------------------------------------------
# R5 — Promo code validator (used by checkout + AJAX toast)
# ---------------------------------------------------------------------------

PROMO_CODES = {
    'STUDENT2026': ('Apple Education Savings — verified via UNiDAYS', 0.10),
    'BACKTOSCHOOL': ('Back to School — AirPods on us with eligible Mac/iPad', 0.0),
    'APPLECARE15': ('AppleCare+ — 15% off with new device', 0.15),
    'TRADEIN50':   ('Trade-in — $50 off your next iPhone', 50.0),
    'FAMILY10':    ('Family Sharing welcome — 10% off Apple One', 0.10),
}


@app.route('/api/promo/validate', methods=['POST'])
@csrf.exempt
def promo_validate():
    """Validate a promo code. Returns success or 400 with a toast-able error."""
    code = (request.values.get('code') or '').strip().upper()
    if not code:
        return jsonify({'valid': False, 'error': 'Enter a promo code.'}), 400
    info = PROMO_CODES.get(code)
    if not info:
        return jsonify({'valid': False, 'error': f'Promo code "{code}" is not valid or has expired.'}), 400
    desc, discount = info
    if 0 < discount < 1:
        savings = f'{int(discount * 100)}% off'
    elif discount >= 1:
        savings = f'${discount:.0f} off'
    else:
        savings = 'Free gift with purchase'
    return jsonify({'valid': True, 'code': code, 'description': desc, 'savings': savings}), 200


# ===========================================================================
# R6 — edge-case routes
#   - /notify-arrival/<slug>            out-of-stock notify-arrival
#   - /configure/<slug>/check           configuration-incompatible warning
#   - /trade-in/imei/verify             trade-in IMEI invalid (strict, no fallback)
#   - /applecare/eligibility            AppleCare-not-eligible
#   - /repair/lookup                    repair-status-not-found (strict)
#   - /gift-card                        age-verification for $500+
# All routes are byte-id safe (deterministic, no DB writes).
# ===========================================================================

R6_OUT_OF_STOCK_SLUGS = {
    'apple-vision-pro', 'mac-pro-tower', 'mac-studio-m2-ultra',
    'airpods-max-2', 'iphone-17-pro-max', 'apple-watch-ultra-3',
    'pro-display-xdr-standard', 'studio-display-nano-tilt',
}


@app.route('/notify-arrival/<slug>', methods=['GET', 'POST'])
@csrf.exempt
def r6_notify_arrival(slug):
    """Out-of-stock notify-arrival flow. POST {email} → notification queued."""
    product = Product.query.filter_by(slug=slug).first_or_404()
    is_oos = (not product.in_stock) or (slug in R6_OUT_OF_STOCK_SLUGS)
    if request.method == 'POST':
        email = (request.values.get('email') or '').strip().lower()
        if not email or '@' not in email or '.' not in email.split('@')[-1]:
            return jsonify({'ok': False, 'error': 'Enter a valid email address.'}), 400
        if not is_oos:
            return jsonify({
                'ok': False, 'product_slug': slug, 'product': product.name,
                'in_stock': True,
                'message': f'{product.name} is currently in stock — no notify-arrival needed.',
            }), 200
        import hashlib
        h = int.from_bytes(hashlib.md5(slug.encode()).digest()[:4], 'big')
        eta_days = 7 + (h % 21)
        return jsonify({
            'ok': True,
            'product_slug': slug, 'product': product.name,
            'email': email,
            'estimated_restock_days': eta_days,
            'estimated_restock_date': (MIRROR_REFERENCE_DATE + timedelta(days=eta_days)).date().isoformat(),
            'priority_queue_position': (h % 500) + 1,
            'message': f'Notify Me — Apple will email {email} as soon as {product.name} returns to stock.',
            'next_step_url': '/retail',
        }), 200
    page = {
        'title': f'Notify When Available — {product.name}',
        'subtitle': ('Currently unavailable.' if is_oos else 'Currently in stock.') +
                    f' Sign up to be emailed when {product.name} ships.',
        'body': [
            f'{product.name} is ' + ('currently out of stock in the requested configuration.' if is_oos else 'in stock today.'),
            'Apple typically restocks high-demand SKUs within 1-4 weeks. POST your email to /notify-arrival/<slug> to be added to the queue.',
            'Prefer in-store pickup? Try /retail to find an Apple Store nearby with stock.',
        ],
        'links': [
            (f'Back to {product.name}', f'/product/{slug}'),
            ('Find an Apple Store', '/retail'),
            ('Apple Trade In', '/trade-in'),
            ('Out-of-stock alternatives', f'/compare/{product.category}'),
        ],
    }
    return render_template('info_page.html', topic=f'notify-arrival/{slug}', page=page)


# Configuration-incompatibility rules (deterministic).
R6_CONFIG_INCOMPAT_RULES = [
    # (slug_prefix, option_a_in_picked, option_b_in_picked, reason)
    ('macbook-air',  {'8GB'},          {'2TB', '4TB', '8TB'},
        'Memory below 16GB is not eligible for 2TB or larger SSD on this model.'),
    ('macbook-pro',  {'18GB', '24GB'}, {'8TB'},
        'M4 Pro chip requires at least 36GB unified memory for 8TB SSD configurations.'),
    ('ipad-pro',     {'Wi-Fi'},        {'eSIM', 'Cellular'},
        'eSIM / Cellular is only available on Wi-Fi + Cellular configurations.'),
    ('iphone-air',   {'Physical SIM'}, {'eSIM-only'},
        'iPhone Air is eSIM-only in this region — physical SIM tray is not supported.'),
    ('apple-watch',  {'GPS'},          {'International Roaming'},
        'International Roaming requires GPS + Cellular.'),
    ('mac-studio',   {'M2 Max'},       {'8TB'},
        '8TB SSD is only available with M2 Ultra. Upgrade chip or choose 4TB.'),
    ('imac',         {'8GB'},          {'2TB', '4TB'},
        'iMac 24" 8GB tier is limited to 256GB-512GB SSD. Upgrade memory for 2TB+.'),
]


@app.route('/configure/<slug>/check', methods=['GET', 'POST'])
@csrf.exempt
def r6_configure_check(slug):
    """Validate a candidate configuration. POST {memory, storage, connectivity, chip}
    → JSON with compatible + warnings list."""
    product = Product.query.filter_by(slug=slug).first_or_404()
    if request.method == 'POST':
        memory = (request.values.get('memory') or '').strip()
        storage = (request.values.get('storage') or '').strip()
        connectivity = (request.values.get('connectivity') or '').strip()
        chip = (request.values.get('chip') or '').strip()
        picked = {x for x in (memory, storage, connectivity, chip) if x}
        warnings = []
        for prefix, set_a, set_b, reason in R6_CONFIG_INCOMPAT_RULES:
            if not product.slug.startswith(prefix):
                continue
            if (set_a & picked) and (set_b & picked):
                warnings.append({
                    'rule': f'{sorted(set_a & picked)} + {sorted(set_b & picked)}',
                    'reason': reason,
                })
        if storage in ('4TB', '8TB') and product.category not in ('mac',):
            warnings.append({
                'rule': f'{storage} on {product.category}',
                'reason': f'{storage} SSD is not offered on this {product.category}. Choose 256GB-1TB.',
            })
        return jsonify({
            'slug': slug, 'memory': memory, 'storage': storage,
            'connectivity': connectivity, 'chip': chip,
            'compatible': not warnings,
            'warnings': warnings,
            'message': ('Configuration is compatible — ready to add to bag.'
                        if not warnings
                        else 'Configuration has 1+ incompatibility — see warnings.'),
            'next_step_url': (f'/configure/{slug}' if warnings else f'/product/{slug}'),
        }), 200
    page = {
        'title': f'Configuration Check — {product.name}',
        'subtitle': 'Validate your custom configuration before adding to bag.',
        'body': [
            f'POST to /configure/{slug}/check with memory + storage + connectivity + chip to validate compatibility.',
            'Sample incompatibility: macbook-air with memory=8GB + storage=2TB returns a warning.',
            'Sample valid: macbook-pro with memory=36GB + storage=4TB on M4 Pro returns compatible=true.',
            'iPad Pro Wi-Fi configurations cannot select eSIM — choose Wi-Fi + Cellular variant.',
        ],
        'links': [
            (f'Configure {product.name}', f'/configure/{slug}'),
            (f'Compare {product.category}', f'/compare/{product.category}'),
            ('Apple Trade In', '/trade-in'),
            ('Financing', '/financing'),
        ],
    }
    return render_template('info_page.html', topic=f'configure/{slug}/check', page=page)


@app.route('/trade-in/imei/verify', methods=['GET', 'POST'])
@csrf.exempt
def r6_trade_in_imei_verify():
    """Strict IMEI verifier — unrecognized IMEIs return 404 with invalid message,
    no fuzzy hash fallback. Complements the existing /trade-in/imei route."""
    imei = (request.values.get('imei') or '').strip().upper()
    if request.method == 'POST':
        if not imei or not imei.isdigit() or len(imei) != 15:
            return jsonify({
                'valid': False, 'imei': imei,
                'error': 'Invalid IMEI format — must be exactly 15 digits.',
                'fix_hint': 'On iPhone, dial *#06# or open Settings > General > About.',
            }), 400
        match = TRADEIN_IMEI_TABLE.get(imei)
        if not match:
            return jsonify({
                'valid': False, 'imei': imei,
                'error': 'IMEI not recognized in Apple Trade In database.',
                'next_step_url': '/trade-in',
                'message': 'Try /trade-in to pick your device manually, or call 1-800-MY-APPLE.',
            }), 404
        device, cond, val = match
        return jsonify({
            'valid': True, 'imei': imei,
            'device_matched': device,
            'condition_default': cond,
            'estimated_value_usd': val,
            'next_step_url': f'/trade-in/quote?device={device}&condition={cond}',
        }), 200
    page = {
        'title': 'Trade In — Verify IMEI (strict)',
        'subtitle': 'Strict IMEI verifier — invalid or unrecognized IMEIs return 404.',
        'body': [
            'POST to /trade-in/imei/verify with imei=<15 digits>. Unlike /trade-in/imei, this endpoint does NOT fall back to a fuzzy match.',
            'Use this when you need an exact match (e.g. fraud-prevention flows).',
            'Sample valid IMEIs: 353299814617852 (iPhone 13), 358901234567890 (iPhone 15).',
            'Sample invalid: 000000000000000 returns 404 with error="IMEI not recognized".',
        ],
        'links': [
            ('Standard IMEI lookup (with fuzzy match)', '/trade-in/imei'),
            ('Trade-in form', '/trade-in'),
            ('Apple Support', '/support'),
        ],
    }
    return render_template('info_page.html', topic='trade-in/imei/verify', page=page)


R6_APPLECARE_NOT_ELIGIBLE_REASONS = [
    ('expired',            'AppleCare+ enrollment window expired (60 days after purchase).'),
    ('damaged',            'Device shows signs of unauthorized modification or non-Apple repair.'),
    ('no-coverage-region', 'AppleCare+ is not available in the registered region.'),
    ('discontinued',       'Coverage is not available for this product model (manufactured pre-2018).'),
]


@app.route('/applecare/eligibility', methods=['GET', 'POST'])
@csrf.exempt
def r6_applecare_eligibility():
    """Check AppleCare+ purchase eligibility — explicit not-eligible path."""
    sn = (request.values.get('serial') or request.values.get('imei') or '').strip().upper()
    if request.method == 'POST':
        if not sn:
            return jsonify({'eligible': False, 'error': 'serial or imei required'}), 400
        import hashlib
        h = int.from_bytes(hashlib.md5(sn.encode()).digest()[:4], 'big')
        if h % 4 == 0:
            key, reason = R6_APPLECARE_NOT_ELIGIBLE_REASONS[h % len(R6_APPLECARE_NOT_ELIGIBLE_REASONS)]
            return jsonify({
                'serial_or_imei': sn,
                'eligible': False,
                'reason_code': key,
                'reason': reason,
                'alternatives': [
                    {'label': 'Self Service Repair',           'url': '/support/repair'},
                    {'label': 'Out-of-warranty Genius Bar',    'url': '/retail'},
                    {'label': 'Apple Limited Warranty info',   'url': '/support/article/warranty'},
                ],
                'support_phone': '1-800-275-2273',
            }), 200
        tier_idx = (h // 4) % 3
        tier_name = ['AppleCare+', 'AppleCare+ with Theft and Loss', 'AppleCare Protection Plan'][tier_idx]
        annual = [149.0, 199.0, 99.0][tier_idx]
        return jsonify({
            'serial_or_imei': sn,
            'eligible': True,
            'recommended_tier': tier_name,
            'annual_price_usd': annual,
            'monthly_price_usd': round(annual / 12, 2),
            'enroll_url': f'/applecare?serial={sn}',
        }), 200
    page = {
        'title': 'AppleCare+ Eligibility',
        'subtitle': 'Verify whether your device can still be enrolled in AppleCare+.',
        'body': [
            'AppleCare+ enrollment window is 60 days from device purchase.',
            'POST to /applecare/eligibility with ?serial=<sn> or ?imei=<imei>.',
            'Common ineligibility reasons: enrollment window expired, unauthorized repair, region not supported, model discontinued.',
            'If ineligible, alternatives include Self Service Repair, Genius Bar (out-of-warranty), or pay-per-incident service.',
        ],
        'links': [
            ('AppleCare coverage check', '/applecare/coverage'),
            ('Compare AppleCare plans', '/applecare-compare'),
            ('Genius Bar (out-of-warranty repair)', '/retail'),
            ('Self Service Repair', '/support/repair'),
        ],
    }
    return render_template('info_page.html', topic='applecare/eligibility', page=page)


@app.route('/repair/lookup', methods=['GET', 'POST'])
@csrf.exempt
def r6_repair_lookup():
    """Strict repair-id lookup — unrecognized IDs return 404 (no hash fallback)."""
    rid = (request.values.get('repair_id') or '').strip().upper()
    if request.method == 'POST':
        if not rid or not rid.startswith('R') or len(rid) != 9 or not rid[1:].isdigit():
            return jsonify({
                'found': False, 'repair_id': rid,
                'error': 'Invalid repair ID format — expected R followed by 8 digits.',
            }), 400
        info = REPAIR_STATUS_TABLE.get(rid)
        if not info:
            return jsonify({
                'found': False, 'repair_id': rid,
                'error': 'Repair ID not found in Apple Service database.',
                'fix_hint': 'Confirm the repair ID from your service confirmation email.',
                'next_step_url': '/support',
            }), 404
        repair, status, eta, location = info
        return jsonify({
            'found': True, 'repair_id': rid,
            'repair': repair, 'status': status,
            'estimated_completion': eta, 'current_location': location,
        }), 200
    page = {
        'title': 'Repair Lookup (strict)',
        'subtitle': 'Look up a repair by ID — unrecognized IDs return 404.',
        'body': [
            'POST to /repair/lookup with repair_id=R<8 digits>. Unlike /repair/status, this endpoint does NOT fall back to a deterministic hash.',
            'Sample valid IDs: R12345678 (iPhone 17 Pro display), R12345679 (MacBook Pro 14 battery).',
            'Sample invalid: R00000000 returns 404 with error="Repair ID not found".',
        ],
        'links': [
            ('Standard repair status (with fallback)', '/repair/status'),
            ('Self Service Repair', '/support/repair'),
            ('Apple Support', '/support'),
        ],
    }
    return render_template('info_page.html', topic='repair/lookup', page=page)


R6_AGEVERIFY_REQUIRED_MIN_USD = 500.0


@app.route('/gift-card', methods=['GET', 'POST'])
@csrf.exempt
def r6_gift_card():
    """Apple Gift Card purchase. Cards >= $500 require dob age-verification (18+)."""
    if request.method == 'POST':
        try:
            amount = float(request.values.get('amount') or 0)
        except (ValueError, TypeError):
            return jsonify({'ok': False, 'error': 'Invalid amount.'}), 400
        recipient_email = (request.values.get('recipient_email') or '').strip().lower()
        dob = (request.values.get('dob') or '').strip()
        if amount <= 0:
            return jsonify({'ok': False, 'error': 'Amount must be positive.'}), 400
        if amount > 2000:
            return jsonify({'ok': False, 'error': 'Maximum gift card value is $2,000 per card.'}), 400
        if amount >= R6_AGEVERIFY_REQUIRED_MIN_USD:
            if not dob:
                return jsonify({
                    'ok': False,
                    'age_verification_required': True,
                    'min_age_years': 18,
                    'threshold_usd': R6_AGEVERIFY_REQUIRED_MIN_USD,
                    'reason': f'Apple Gift Cards of ${R6_AGEVERIFY_REQUIRED_MIN_USD:.0f} or more require age verification (18+).',
                    'next_step': 'POST again with dob=YYYY-MM-DD.',
                }), 200
            try:
                birth = datetime.strptime(dob, '%Y-%m-%d')
            except ValueError:
                return jsonify({'ok': False, 'error': 'Invalid dob — use YYYY-MM-DD.'}), 400
            age = (MIRROR_REFERENCE_DATE - birth).days // 365
            if age < 18:
                return jsonify({
                    'ok': False,
                    'verified_age': age,
                    'age_verification_required': True,
                    'error': f'You must be at least 18 to purchase a gift card of ${amount:.0f}.',
                }), 200
        import hashlib
        code_seed = f'{amount:.2f}|{recipient_email}'
        code = 'X' + hashlib.md5(code_seed.encode()).hexdigest()[:15].upper()
        return jsonify({
            'ok': True,
            'amount_usd': amount,
            'recipient_email': recipient_email,
            'gift_card_code': code,
            'age_verified': amount >= R6_AGEVERIFY_REQUIRED_MIN_USD,
            'delivery': ('Email within 24 hours' if recipient_email else 'Available in your Apple account'),
            'add_to_wallet_url': '/wallet/add?pass=gift-card',
        }), 200
    page = {
        'title': 'Apple Gift Card',
        'subtitle': f'Send a digital Apple Gift Card by email. Cards ${int(R6_AGEVERIFY_REQUIRED_MIN_USD)}+ require age verification.',
        'body': [
            'Apple Gift Cards work for everything Apple — products, accessories, AppleCare, App Store, iCloud+, Apple Music, and more.',
            'POST to /gift-card with amount + recipient_email to purchase.',
            f'Cards of ${int(R6_AGEVERIFY_REQUIRED_MIN_USD)} or more require dob (YYYY-MM-DD) for 18+ age verification.',
            'Maximum gift card value is $2,000 per card. Purchase multiple cards for higher amounts.',
            'Sample amounts: $25, $50, $100, $250 (no age verify); $500, $1000, $2000 (age verify required).',
        ],
        'links': [
            ('Gift Cards FAQ', '/support/article/gift-cards'),
            ('Add to Apple Wallet', '/wallet/add?pass=gift-card'),
            ('Send another gift', '/shop?category=accessories'),
            ('Apple Card', '/apple-card'),
        ],
    }
    return render_template('info_page.html', topic='gift-card', page=page)


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

def seed_database():
    """Populate database with Apple products."""
    if Product.query.first():
        return

    products = [
        # iPhone
        Product(name='iPhone 17 Pro', slug='iphone-17-pro', category='iphone',
                subtitle='All out Pro.', description='The most advanced iPhone ever with A19 Pro chip, titanium design, and a 48MP camera system with 8x optical-quality zoom.',
                price=1099.00, monthly_price=45.79, months=24, is_new=True, is_featured=True,
                image='/static/images/products/iphone_17_pro.jpg', hero_image='/static/images/hero/iphone_17_pro_hero.jpg',
                color_options=json.dumps(['Natural Titanium', 'Black Titanium', 'White Titanium', 'Sand Titanium']),
                storage_options=json.dumps(['256GB', '512GB', '1TB']),
                specs=json.dumps({'chip': 'A19 Pro', 'display': '6.3" Super Retina XDR', 'camera': '48MP Main + 48MP Ultra Wide + 12MP Telephoto', 'battery': 'Up to 33 hours video playback'})),
        Product(name='iPhone 17 Pro Max', slug='iphone-17-pro-max', category='iphone',
                subtitle='The biggest Pro ever.', description='Massive 6.9-inch display, A19 Pro chip, and the longest battery life ever in an iPhone.',
                price=1199.00, monthly_price=49.95, months=24, is_new=True, is_featured=True,
                image='/static/images/products/iphone_17_pro_max.jpg', hero_image='/static/images/hero/iphone_17_pro_max_hero.jpg',
                color_options=json.dumps(['Natural Titanium', 'Black Titanium', 'White Titanium', 'Sand Titanium']),
                storage_options=json.dumps(['256GB', '512GB', '1TB']),
                specs=json.dumps({'chip': 'A19 Pro', 'display': '6.9" Super Retina XDR', 'camera': '48MP Main + 48MP Ultra Wide + 12MP Telephoto', 'battery': 'Up to 39 hours video playback'})),
        Product(name='iPhone Air', slug='iphone-air', category='iphone',
                subtitle='The thinnest iPhone ever.', description='Incredibly thin and light design with the power of pro inside.',
                price=999.00, monthly_price=41.62, months=24, is_new=True, is_featured=True,
                image='/static/images/products/iphone_air.jpg', hero_image='/static/images/hero/iphone_air_hero.jpg',
                color_options=json.dumps(['Midnight', 'Starlight', 'Green', 'Blue', 'Pink']),
                storage_options=json.dumps(['128GB', '256GB', '512GB']),
                specs=json.dumps({'chip': 'A18', 'display': '6.6" Super Retina XDR', 'camera': '48MP Main + 12MP Ultra Wide', 'battery': 'Up to 30 hours video playback'})),
        Product(name='iPhone 17', slug='iphone-17', category='iphone',
                subtitle='Even more delightful. Even more durable.', description='Beautiful design with Ceramic Shield 2 and Dynamic Island.',
                price=799.00, monthly_price=33.29, months=24, is_new=True, is_featured=True,
                image='/static/images/products/iphone_17.jpg', hero_image='/static/images/hero/iphone_17_hero.jpg',
                color_options=json.dumps(['Black', 'White', 'Pink', 'Green', 'Blue']),
                storage_options=json.dumps(['128GB', '256GB', '512GB']),
                specs=json.dumps({'chip': 'A18', 'display': '6.1" Super Retina XDR', 'camera': '48MP Main + 12MP Ultra Wide', 'battery': 'Up to 28 hours video playback'})),
        Product(name='iPhone 17e', slug='iphone-17e', category='iphone',
                subtitle='Feature stacked. Value packed.', description='Everything you need in an iPhone at an amazing price.',
                price=599.00, monthly_price=24.95, months=24, is_new=True, is_featured=True,
                image='/static/images/products/iphone_17e.jpg', hero_image='/static/images/hero/iphone_17e_hero.jpg',
                color_options=json.dumps(['Black', 'White', 'Pink', 'Green']),
                storage_options=json.dumps(['128GB', '256GB']),
                specs=json.dumps({'chip': 'A18', 'display': '6.1" Super Retina XDR', 'camera': '48MP Main', 'battery': 'Up to 26 hours video playback'})),
        # Mac
        Product(name='MacBook Neo', slug='macbook-neo', category='mac',
                subtitle='Hello, Neo. The magic of Mac at a surprising price.', description='A18 Pro chip, 13-inch Liquid Retina display, up to 16 hours of battery life. Available in four stunning colors.',
                price=599.00, monthly_price=24.95, months=24, is_new=True, is_featured=True,
                image='/static/images/products/macbook_neo.jpg', hero_image='/static/images/hero/macbook_neo_hero.jpg',
                color_options=json.dumps(['Silver', 'Blush', 'Citrus', 'Indigo']),
                storage_options=json.dumps(['256GB', '512GB']),
                specs=json.dumps({'chip': 'A18 Pro', 'display': '13" Liquid Retina', 'memory': '8GB', 'battery': 'Up to 16 hours'})),
        Product(name='MacBook Pro 14"', slug='macbook-pro-14', category='mac',
                subtitle='Outrageously powerful.', description='M5 chip, stunning Liquid Retina XDR display, and all-day battery life.',
                price=1699.00, monthly_price=70.79, months=24, is_new=True, is_featured=True,
                image='/static/images/products/macbook_pro_14.jpg', hero_image='/static/images/hero/macbook_pro_14_hero.jpg',
                color_options=json.dumps(['Space Black', 'Silver']),
                storage_options=json.dumps(['512GB', '1TB', '2TB']),
                specs=json.dumps({'chip': 'M5', 'display': '14.2" Liquid Retina XDR', 'memory': '24GB', 'battery': 'Up to 22 hours'})),
        Product(name='MacBook Pro 16"', slug='macbook-pro-16', category='mac',
                subtitle='The most powerful MacBook Pro ever.', description='M5 Pro or M5 Max chip for the ultimate pro notebook.',
                price=2499.00, monthly_price=104.12, months=24, is_new=True, is_featured=False,
                image='/static/images/products/macbook_pro_16.png', hero_image='/static/images/hero/macbook_pro_16_hero.jpg',
                color_options=json.dumps(['Space Black', 'Silver']),
                storage_options=json.dumps(['512GB', '1TB', '2TB', '4TB']),
                specs=json.dumps({'chip': 'M5 Pro / M5 Max', 'display': '16.2" Liquid Retina XDR', 'memory': '36GB / 48GB', 'battery': 'Up to 24 hours'})),
        Product(name='MacBook Air 13"', slug='macbook-air-13', category='mac',
                subtitle='Lean. Mean. Icons machine.', description='M5 chip in an impossibly thin design.',
                price=1099.00, monthly_price=45.79, months=24, is_new=True, is_featured=True,
                image='/static/images/products/macbook_air_13.png', hero_image='/static/images/hero/macbook_air_13_hero.png',
                color_options=json.dumps(['Midnight', 'Starlight', 'Space Gray', 'Silver']),
                storage_options=json.dumps(['256GB', '512GB', '1TB']),
                specs=json.dumps({'chip': 'M5', 'display': '13.6" Liquid Retina', 'memory': '16GB', 'battery': 'Up to 18 hours'})),
        Product(name='iMac 24"', slug='imac-24', category='mac',
                subtitle='Say hello.', description='M5 chip, stunning 24-inch 4.5K Retina display, and a colorful all-in-one design.',
                price=1299.00, monthly_price=54.12, months=24, is_new=False, is_featured=False,
                image='/static/images/products/imac.jpg', hero_image='/static/images/hero/imac_hero.jpg',
                color_options=json.dumps(['Blue', 'Green', 'Pink', 'Silver', 'Yellow', 'Orange', 'Purple']),
                storage_options=json.dumps(['256GB', '512GB', '1TB']),
                specs=json.dumps({'chip': 'M5', 'display': '24" 4.5K Retina', 'memory': '16GB', 'battery': 'N/A (Desktop)'})),
        # iPad
        Product(name='iPad Air M4', slug='ipad-air-m4', category='ipad',
                subtitle='Now supercharged by M4.', description='M4 chip with 8-core CPU, Liquid Retina display, and Apple Pencil Pro support.',
                price=599.00, monthly_price=24.95, months=24, is_new=True, is_featured=True,
                image='/static/images/products/ipad_air.png', hero_image='/static/images/hero/ipad_air_hero.png',
                color_options=json.dumps(['Space Gray', 'Blue', 'Purple', 'Starlight']),
                storage_options=json.dumps(['128GB', '256GB', '512GB', '1TB']),
                specs=json.dumps({'chip': 'M4', 'display': '11" or 13" Liquid Retina', 'camera': '12MP Wide', 'battery': 'Up to 10 hours'})),
        Product(name='iPad Pro M5', slug='ipad-pro-m5', category='ipad',
                subtitle='Unbelievably thin. Incredibly powerful.', description='M5 chip, Ultra Retina XDR display, and Thunderbolt connectivity.',
                price=999.00, monthly_price=41.62, months=24, is_new=True, is_featured=False,
                image='/static/images/products/ipad_pro.jpg', hero_image='/static/images/hero/ipad_pro_hero.png',
                color_options=json.dumps(['Space Black', 'Silver']),
                storage_options=json.dumps(['256GB', '512GB', '1TB', '2TB']),
                specs=json.dumps({'chip': 'M5', 'display': '11" or 13" Ultra Retina XDR', 'camera': '12MP Wide + LiDAR', 'battery': 'Up to 10 hours'})),
        Product(name='iPad 10th Gen', slug='ipad-10', category='ipad',
                subtitle='Colorful. Powerful. Wonderful.', description='A14 Bionic chip, 10.9-inch Liquid Retina display.',
                price=349.00, monthly_price=14.54, months=24, is_new=False, is_featured=False,
                image='/static/images/products/ipad_10.png', hero_image='/static/images/hero/ipad_10_hero.png',
                color_options=json.dumps(['Blue', 'Pink', 'Yellow', 'Silver']),
                storage_options=json.dumps(['64GB', '256GB']),
                specs=json.dumps({'chip': 'A14 Bionic', 'display': '10.9" Liquid Retina', 'camera': '12MP Wide', 'battery': 'Up to 10 hours'})),
        # Watch
        Product(name='Apple Watch Series 11', slug='apple-watch-series-11', category='watch',
                subtitle='The ultimate way to watch your health.', description='Hypertension notifications, sleep score, S10 chip, Always-On Retina display.',
                price=399.00, monthly_price=16.62, months=24, is_new=True, is_featured=True,
                image='/static/images/products/watch_series_11.png', hero_image='/static/images/hero/watch_series_11_hero.png',
                color_options=json.dumps(['Rose Gold', 'Silver', 'Jet Black', 'Space Gray']),
                storage_options=json.dumps(['42mm', '46mm']),
                specs=json.dumps({'chip': 'S10', 'display': 'Always-On Retina LTPO3', 'health': 'Blood oxygen, ECG, Temperature sensing', 'battery': 'Up to 24 hours'})),
        Product(name='Apple Watch Ultra 3', slug='apple-watch-ultra-3', category='watch',
                subtitle='The most capable Apple Watch ever.', description='49mm titanium case, precision dual-frequency GPS, and up to 72 hours of battery life.',
                price=799.00, monthly_price=33.29, months=24, is_new=True, is_featured=False,
                image='/static/images/products/watch_ultra.png', hero_image='/static/images/hero/watch_ultra_hero.png',
                color_options=json.dumps(['Natural Titanium', 'Black Titanium']),
                storage_options=json.dumps(['49mm']),
                specs=json.dumps({'chip': 'S10', 'display': '49mm Always-On Retina', 'health': 'Blood oxygen, ECG, Temperature, Depth gauge', 'battery': 'Up to 72 hours'})),
        # AirPods
        Product(name='AirPods Pro 3', slug='airpods-pro-3', category='airpods',
                subtitle='Intelligent hearing. Brilliant sound.', description='Active Noise Cancellation, Adaptive Audio, and a hearing health experience.',
                price=249.00, monthly_price=10.37, months=24, is_new=True, is_featured=True,
                image='/static/images/products/airpods_pro.jpg', hero_image='/static/images/hero/airpods_pro_hero.png',
                color_options=json.dumps(['White']),
                storage_options=json.dumps([]),
                specs=json.dumps({'chip': 'H3', 'anc': 'Active Noise Cancellation', 'audio': 'Personalized Spatial Audio', 'battery': 'Up to 6 hours (30 hours with case)'})),
        Product(name='AirPods Max 2', slug='airpods-max-2', category='airpods',
                subtitle='New intelligent features. Same icons sound.', description='High-fidelity audio with Active Noise Cancellation and USB-C.',
                price=549.00, monthly_price=22.87, months=24, is_new=True, is_featured=True,
                image='/static/images/products/airpods_max.png', hero_image='/static/images/hero/airpods_max_hero.png',
                color_options=json.dumps(['Midnight', 'Blue', 'Purple', 'Orange', 'Starlight']),
                storage_options=json.dumps([]),
                specs=json.dumps({'chip': 'H3', 'anc': 'Active Noise Cancellation', 'audio': 'Personalized Spatial Audio with head tracking', 'battery': 'Up to 20 hours'})),
        Product(name='AirPods 4', slug='airpods-4', category='airpods',
                subtitle='Iconic. Now in Icons.', description='Open-ear design for all-day comfort.',
                price=129.00, monthly_price=5.37, months=24, is_new=False, is_featured=False,
                image='/static/images/products/airpods_4.jpg', hero_image='/static/images/hero/airpods_4_hero.jpg',
                color_options=json.dumps(['White']),
                storage_options=json.dumps([]),
                specs=json.dumps({'chip': 'H2', 'audio': 'Personalized Spatial Audio', 'battery': 'Up to 5 hours (30 hours with case)'})),
        # Accessories
        Product(name='Apple Pencil Pro', slug='apple-pencil-pro', category='accessories',
                subtitle='Built for the most demanding workflows.', description='Apple Pencil Pro features Squeeze, barrel roll, and haptic feedback. Wireless pairing and wireless charging for effortless setup. Hover to preview before you draw.',
                price=129.00, monthly_price=5.37, months=24, is_new=False, is_featured=False,
                image='/static/images/products/apple_pencil.jpg', hero_image='/static/images/hero/apple_pencil_hero.jpg',
                color_options=json.dumps(['White']),
                storage_options=json.dumps([]),
                specs=json.dumps({'features': 'Squeeze, Barrel roll, Haptic feedback, Hover, Wireless pairing, wireless charging'})),
        Product(name='Apple Pencil (2nd generation)', slug='apple-pencil-2nd-gen', category='accessories',
                subtitle='A new sense of touch.', description='Apple Pencil 2nd generation magnetically attaches, pairs, and charges. Double-tap to switch tools.',
                price=129.00, monthly_price=5.37, months=24, is_new=False, is_featured=False,
                image='/static/images/products/apple_pencil_2.jpg', hero_image='/static/images/hero/apple_pencil_2_hero.jpg',
                color_options=json.dumps(['White']),
                storage_options=json.dumps([]),
                specs=json.dumps({'features': 'Magnetic attach, Wireless pairing, wireless charging, Double-tap gesture'})),
        Product(name='Apple Pencil (USB-C)', slug='apple-pencil-usb-c', category='accessories',
                subtitle='Write and draw with precision.', description='Apple Pencil with USB-C connector for easy pairing and charging.',
                price=79.00, monthly_price=3.29, months=24, is_new=False, is_featured=False,
                image='/static/images/products/apple_pencil_usbc.jpg', hero_image='/static/images/hero/apple_pencil_usbc_hero.jpg',
                color_options=json.dumps(['White']),
                storage_options=json.dumps([]),
                specs=json.dumps({'features': 'USB-C pairing and charging, Pixel-perfect precision, Tilt sensitivity'})),
        Product(name='Magic Keyboard for iPad', slug='magic-keyboard-ipad', category='accessories',
                subtitle='The best way to type on iPad.', description='Full-size keyboard with trackpad, backlit keys, and USB-C port.',
                price=299.00, monthly_price=12.45, months=24, is_new=False, is_featured=False,
                image='/static/images/products/magic_keyboard.png', hero_image='/static/images/hero/magic_keyboard_hero.png',
                color_options=json.dumps(['White', 'Black']),
                storage_options=json.dumps([]),
                specs=json.dumps({'features': 'Backlit keys, Trackpad, USB-C passthrough'})),
        Product(name='AirTag', slug='airtag', category='accessories',
                subtitle='Lose your knack for losing things.', description='Precision Finding with Ultra Wideband.',
                price=29.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/airtag.jpg', hero_image='/static/images/hero/airtag_hero.jpg',
                color_options=json.dumps(['Silver']),
                storage_options=json.dumps([]),
                specs=json.dumps({'features': 'Precision Finding, Replaceable battery, IP67 water resistant'})),
        # --- MacBook Air 15" (M3) ---
        Product(name='MacBook Air 15"', slug='macbook-air-15', category='mac',
                subtitle='Impressively big. Impossibly thin.',
                description='M5 chip in a 15-inch Liquid Retina display, up to 18 hours of battery life.',
                price=1299.00, monthly_price=54.12, months=24, is_new=True, is_featured=False,
                image='/static/images/products/macbook_air_15.jpg', hero_image='/static/images/hero/macbook_air_15_hero.jpg',
                color_options=json.dumps(['Midnight', 'Starlight', 'Space Gray', 'Silver']),
                storage_options=json.dumps(['256GB', '512GB', '1TB']),
                specs=json.dumps({'chip': 'M5', 'display': '15.3" Liquid Retina', 'memory': '16GB', 'battery': 'Up to 18 hours'}),
                chip_family='M5', ram=16, screen_size=15.3, release_year=2025),
        Product(name='MacBook Air 13-inch M3', slug='macbook-air-13-inch-m3', category='mac', subcategory='macbook-air',
                subtitle='Lean. Mean. Icons machine.',
                description='M3 chip, 13.6-inch Liquid Retina display, up to 18 hours of battery life. Available in four stunning colors. 8GB unified memory, 256GB SSD.',
                price=1099.00, monthly_price=45.79, months=24, is_new=False, is_featured=False,
                image='/static/images/products/macbook_air_13_m3.jpg', hero_image='/static/images/hero/macbook_air_13_m3_hero.jpg',
                color_options=json.dumps(['Midnight', 'Starlight', 'Space Gray', 'Silver']),
                storage_options=json.dumps(['256GB', '512GB', '1TB']),
                specs=json.dumps({'chip': 'M3', 'display': '13.6" Liquid Retina', 'memory': '8GB unified memory', 'battery': 'Up to 15 hours web browsing', 'SSD': '256GB / 512GB / 1TB'}),
                chip_family='M3', ram=8, ssd=256, screen_size=13.6, release_year=2024,
                battery_life='Up to 15 hours web browsing'),
        Product(name='MacBook Air 15-inch M3', slug='macbook-air-15-inch-m3', category='mac', subcategory='macbook-air',
                subtitle='Impressively big. Impossibly thin.',
                description='M3 chip in a 15-inch Liquid Retina display.',
                price=1299.00, monthly_price=54.12, months=24, is_new=False, is_featured=False,
                image='/static/images/products/macbook_air_15_m3.jpg', hero_image='/static/images/hero/macbook_air_15_m3_hero.jpg',
                color_options=json.dumps(['Midnight', 'Starlight', 'Space Gray', 'Silver']),
                storage_options=json.dumps(['256GB', '512GB', '1TB']),
                specs=json.dumps({'chip': 'M3', 'display': '15.3" Liquid Retina', 'memory': '8GB', 'battery': 'Up to 18 hours'}),
                chip_family='M3', ram=8, screen_size=15.3, release_year=2024),
        # --- MacBook Pro M3 variants ---
        Product(name='MacBook Pro 14-inch M3', slug='macbook-pro-14-inch-m3', category='mac', subcategory='macbook-pro',
                subtitle='Mind-blowing. Head-turning.',
                description='M3 chip, 14.2-inch Liquid Retina XDR display, 18 hours of battery life. Configurable with up to 24GB unified memory, 2TB SSD.',
                price=1599.00, monthly_price=66.62, months=24, is_new=False, is_featured=False,
                image='/static/images/products/macbook_pro_14_m3.jpg', hero_image='/static/images/hero/macbook_pro_14_m3_hero.jpg',
                color_options=json.dumps(['Space Black', 'Silver']),
                storage_options=json.dumps(['512GB', '1TB', '2TB']),
                specs=json.dumps({'chip': 'M3', 'display': '14.2" Liquid Retina XDR', 'memory': '8GB / 16GB / 24GB unified memory', 'battery': 'Up to 22 hours', 'storage': '512GB / 1TB / 2TB SSD'}),
                chip_family='M3', ram=8, ssd=512, screen_size=14.2, release_year=2023,
                slogan='Mind-blowing. Head-turning.',
                config_upgrades=json.dumps({
                    'memory': ['8GB Unified Memory', '16GB Unified Memory (+$200)', '24GB Unified Memory (+$400)'],
                    'storage': ['512GB SSD', '1TB SSD (+$200)', '2TB SSD (+$400)'],
                    'Upgrade': 'Upgrade options available'
                }),
                keyboard_options=json.dumps([
                    'Backlit Magic Keyboard with Touch ID — US English',
                    'Backlit Magic Keyboard with Touch ID — British English',
                    'Backlit Magic Keyboard with Touch ID — French',
                    'Backlit Magic Keyboard with Touch ID — German',
                    'Backlit Magic Keyboard with Touch ID — Spanish',
                    'Backlit Magic Keyboard with Touch ID — Japanese',
                ])),
        Product(name='MacBook Pro 16-inch M3 Max', slug='macbook-pro-16-inch-m3-max', category='mac', subcategory='macbook-pro',
                subtitle='The most powerful MacBook Pro ever.',
                description='M3 Max chip with 16-core CPU and 40-core GPU, 64GB unified memory, 1TB SSD. Massive 16.2-inch Liquid Retina XDR display.',
                price=3499.00, monthly_price=145.79, months=24, is_new=False, is_featured=False,
                image='/static/images/products/macbook_pro_16_m3.jpg', hero_image='/static/images/hero/macbook_pro_16_m3_hero.jpg',
                color_options=json.dumps(['Space Black', 'Silver']),
                storage_options=json.dumps(['1TB', '2TB', '4TB', '8TB']),
                specs=json.dumps({'chip': 'M3 Max', 'cpu': '16-core CPU', 'gpu': '40-core GPU', 'memory': '64GB unified memory', 'storage': '1TB SSD', 'display': '16.2" Liquid Retina XDR', 'battery': 'Up to 22 hours'}),
                chip_family='M3 Max', ram=64, ssd=1000, cpu_cores=16, gpu_cores=40, screen_size=16.2, release_year=2023),
        # --- iMac M3 ---
        Product(name='iMac 24-inch M3', slug='imac-24-inch-m3', category='mac', subcategory='imac',
                subtitle='Say hello.',
                description='M3 chip, stunning 24-inch 4.5K Retina display, and a colorful all-in-one design.',
                price=1299.00, monthly_price=54.12, months=24, is_new=False, is_featured=False,
                image='/static/images/products/imac_m3.jpg', hero_image='/static/images/hero/imac_m3_hero.jpg',
                color_options=json.dumps(['Blue', 'Green', 'Pink', 'Silver', 'Yellow', 'Orange', 'Purple']),
                storage_options=json.dumps(['256GB', '512GB', '1TB']),
                specs=json.dumps({'chip': 'M3', 'display': '24" 4.5K Retina', 'memory': '8GB / 16GB / 24GB', 'battery': 'N/A (Desktop)'}),
                chip_family='M3', ram=8, screen_size=24.0, release_year=2023),
        # --- Mac mini M2 Pro ---
        Product(name='Mac mini M2 Pro', slug='mac-mini-m2-pro', category='mac', subcategory='mac-mini',
                subtitle='More muscle. More hustle.',
                description='M2 Pro chip with 12-core CPU and 19-core GPU. 16GB unified memory with option for 32GB. Supports up to 16-core CPU and 19-core GPU for maximum performance.',
                price=1399.00, monthly_price=58.29, months=24, is_new=False, is_featured=False,
                image='/static/images/products/mac_mini.jpg', hero_image='/static/images/hero/mac_mini_hero.jpg',
                color_options=json.dumps(['Silver']),
                storage_options=json.dumps(['512GB', '1TB', '2TB']),
                specs=json.dumps({'chip': 'M2 Pro', 'cpu': '12-core CPU / upgrade to 16-core CPU', 'gpu': '19-core GPU', 'memory': '16GB / 32GB unified memory'}),
                chip_family='M2 Pro', ram=16, ssd=512, cpu_cores=12, gpu_cores=19, release_year=2023),
        # --- Mac product page ---
        Product(name='Mac', slug='mac', category='mac', subcategory='mac-landing',
                subtitle='If you can dream it, Mac can do it.',
                description='Explore the full Mac lineup: MacBook Air, MacBook Pro, iMac, Mac mini, Mac Studio, and Mac Pro. If you can dream it, Mac can do it.',
                price=599.00, monthly_price=24.95, months=24, is_new=False, is_featured=False,
                image='/static/images/products/mac_lineup.jpg', hero_image='/static/images/hero/mac_hero.jpg',
                color_options=json.dumps([]),
                storage_options=json.dumps([]),
                specs=json.dumps({}),
                slogan='If you can dream it, Mac can do it.'),
        # --- Older iPhones ---
        Product(name='iPhone 15 Pro', slug='iphone-15-pro', category='iphone',
                subtitle='Titanium. So strong. So light. So Pro.',
                description='A17 Pro chip, titanium design, 48MP main camera with 5x optical zoom. Available in four stunning titanium finishes.',
                price=999.00, monthly_price=41.62, months=24, is_new=False, is_featured=False,
                image='/static/images/products/iphone_15_pro.jpg', hero_image='/static/images/hero/iphone_15_pro_hero.jpg',
                color_options=json.dumps(['Natural Titanium', 'Blue Titanium', 'White Titanium', 'Black Titanium']),
                storage_options=json.dumps(['128GB', '256GB', '512GB', '1TB']),
                specs=json.dumps({'chip': 'A17 Pro', 'display': '6.1" Super Retina XDR', 'camera': '48MP Main + 12MP Ultra Wide + 12MP 5x Telephoto', 'battery': 'Up to 23 hours video playback'}),
                chip_family='A17 Pro', release_year=2023, release_date='September 22, 2023'),
        Product(name='iPhone 15 Pro Max', slug='iphone-15-pro-max', category='iphone',
                subtitle='Titanium. So strong. So light. So Pro.',
                description='A17 Pro chip, titanium design, 48MP main camera system.',
                price=1199.00, monthly_price=49.95, months=24, is_new=False, is_featured=False,
                image='/static/images/products/iphone_15_pro_max.jpg', hero_image='/static/images/hero/iphone_15_pro_max_hero.jpg',
                color_options=json.dumps(['Natural Titanium', 'Blue Titanium', 'White Titanium', 'Black Titanium']),
                storage_options=json.dumps(['256GB', '512GB', '1TB']),
                specs=json.dumps({'chip': 'A17 Pro', 'display': '6.7" Super Retina XDR', 'camera': '48MP Main + 12MP Ultra Wide + 12MP 5x Telephoto'}),
                chip_family='A17 Pro', release_year=2023),
        Product(name='iPhone 14 Pro', slug='iphone-14-pro', category='iphone',
                subtitle='Pro. Beyond.',
                description='A16 Bionic chip, Always-On display, Dynamic Island, and a 48MP main camera.',
                price=999.00, monthly_price=41.62, months=24, is_new=False, is_featured=False,
                image='/static/images/products/iphone_14_pro.jpg', hero_image='/static/images/hero/iphone_14_pro_hero.jpg',
                color_options=json.dumps(['Deep Purple', 'Gold', 'Silver', 'Space Black']),
                storage_options=json.dumps(['128GB', '256GB', '512GB', '1TB']),
                specs=json.dumps({'chip': 'A16 Bionic', 'display': '6.1" Super Retina XDR', 'camera': '48MP Main + 12MP Ultra Wide + 12MP Telephoto'}),
                chip_family='A16', release_year=2022, release_date='September 16, 2022'),
        Product(name='iPhone 14 Pro Max', slug='iphone-14-pro-max', category='iphone',
                subtitle='Pro. Beyond.',
                description='A16 Bionic chip, 6.7-inch Always-On Super Retina XDR display, Dynamic Island, 48MP camera system.',
                price=1099.00, monthly_price=45.79, months=24, is_new=False, is_featured=False,
                image='/static/images/products/iphone_14_pro_max.jpg', hero_image='/static/images/hero/iphone_14_pro_max_hero.jpg',
                color_options=json.dumps(['Deep Purple', 'Gold', 'Silver', 'Space Black']),
                storage_options=json.dumps(['128GB', '256GB', '512GB', '1TB']),
                specs=json.dumps({'chip': 'A16 Bionic', 'display': '6.7" Super Retina XDR'}),
                chip_family='A16', release_year=2022),
        Product(name='iPhone 14 Plus', slug='iphone-14-plus', category='iphone',
                subtitle='Big and bigger.',
                description='A15 Bionic chip, 6.7-inch Super Retina XDR display with the longest battery life ever in an iPhone.',
                price=899.00, monthly_price=37.45, months=24, is_new=False, is_featured=False,
                image='/static/images/products/iphone_14_plus.jpg', hero_image='/static/images/hero/iphone_14_plus_hero.jpg',
                color_options=json.dumps(['Midnight', 'Starlight', 'Blue', 'Purple', 'Red', 'Yellow']),
                storage_options=json.dumps(['128GB', '256GB', '512GB']),
                specs=json.dumps({'chip': 'A15 Bionic', 'display': '6.7" Super Retina XDR', 'camera': '12MP dual camera'}),
                chip_family='A15', release_year=2022),
        Product(name='iPhone 13 Pro', slug='iphone-13-pro', category='iphone',
                subtitle='Oh. So. Pro.',
                description='A15 Bionic chip, ProMotion, and a pro camera system.',
                price=999.00, monthly_price=41.62, months=24, is_new=False, is_featured=False,
                image='/static/images/products/iphone_13_pro.jpg', hero_image='/static/images/hero/iphone_13_pro_hero.jpg',
                color_options=json.dumps(['Sierra Blue', 'Silver', 'Gold', 'Graphite', 'Alpine Green']),
                storage_options=json.dumps(['128GB', '256GB', '512GB', '1TB']),
                specs=json.dumps({'chip': 'A15 Bionic', 'display': '6.1" Super Retina XDR with ProMotion', 'camera': '12MP triple camera'}),
                chip_family='A15', release_year=2021),
        Product(name='iPhone 13 Pro Max', slug='iphone-13-pro-max', category='iphone',
                subtitle='Oh. So. Pro.',
                description='A15 Bionic chip, 6.7-inch ProMotion display, and longest battery life ever.',
                price=1099.00, monthly_price=45.79, months=24, is_new=False, is_featured=False,
                image='/static/images/products/iphone_13_pro_max.jpg', hero_image='/static/images/hero/iphone_13_pro_max_hero.jpg',
                color_options=json.dumps(['Sierra Blue', 'Silver', 'Gold', 'Graphite', 'Alpine Green']),
                storage_options=json.dumps(['128GB', '256GB', '512GB', '1TB']),
                specs=json.dumps({'chip': 'A15 Bionic', 'display': '6.7" Super Retina XDR with ProMotion'}),
                chip_family='A15', release_year=2021),
        # --- iPad Pro M4 variants ---
        Product(name='iPad Pro 13-inch M4', slug='ipad-pro-13-inch-m4', category='ipad', subcategory='ipad-pro',
                subtitle='Unbelievably thin. Incredibly powerful.',
                description='M4 chip, 13-inch Ultra Retina XDR display with ProMotion and P3 wide colour, Thunderbolt / USB 4 connector.',
                price=1299.00, monthly_price=54.12, months=24, is_new=False, is_featured=False,
                image='/static/images/products/ipad_pro_13_m4.jpg', hero_image='/static/images/hero/ipad_pro_13_m4_hero.jpg',
                color_options=json.dumps(['Space Black', 'Silver']),
                storage_options=json.dumps(['256GB', '512GB', '1TB', '2TB']),
                specs=json.dumps({'chip': 'M4', 'display': '13" Ultra Retina XDR with ProMotion', 'camera': '12MP Wide + LiDAR'}),
                chip_family='M4', release_year=2024, release_date='May 15, 2024'),
        Product(name='iPad Pro 11-inch M4', slug='ipad-pro-11-inch-m4', category='ipad', subcategory='ipad-pro',
                subtitle='Unbelievably thin. Incredibly powerful.',
                description='M4 chip, 11-inch Ultra Retina XDR display, LiDAR Scanner.',
                price=999.00, monthly_price=41.62, months=24, is_new=False, is_featured=False,
                image='/static/images/products/ipad_pro_11_m4.jpg', hero_image='/static/images/hero/ipad_pro_11_m4_hero.jpg',
                color_options=json.dumps(['Space Black', 'Silver']),
                storage_options=json.dumps(['256GB', '512GB', '1TB', '2TB']),
                specs=json.dumps({'chip': 'M4', 'display': '11" Ultra Retina XDR', 'camera': '12MP Wide + LiDAR'}),
                chip_family='M4', release_year=2024, release_date='May 15, 2024'),
        # --- iPad mini ---
        Product(name='iPad mini', slug='ipad-mini', category='ipad', subcategory='ipad-mini',
                subtitle='Mega power. Mini icons.',
                description='A17 Pro chip, 8.3-inch Liquid Retina display, Apple Pencil Pro support. 4K video recording at 60 fps.',
                price=499.00, monthly_price=20.79, months=24, is_new=False, is_featured=False,
                image='/static/images/products/ipad_mini.jpg', hero_image='/static/images/hero/ipad_mini_hero.jpg',
                color_options=json.dumps(['Space Gray', 'Blue', 'Purple', 'Starlight']),
                storage_options=json.dumps(['128GB', '256GB', '512GB']),
                specs=json.dumps({'chip': 'A17 Pro', 'display': '8.3" Liquid Retina', 'camera': '12MP Wide', 'video': '4K video recording at 60 fps'}),
                chip_family='A17 Pro', video_recording='4K video recording at 60 fps', release_year=2024),
        Product(name='iPad mini 64GB Wi-Fi + Cellular', slug='ipad-mini-64gb-wi-fi-cellular', category='ipad', subcategory='ipad-mini',
                subtitle='Mega power. Mini icons.',
                description='iPad mini with A15 Bionic chip, 64GB storage, Wi-Fi + Cellular connectivity.',
                price=649.00, monthly_price=27.04, months=24, is_new=False, is_featured=False,
                image='/static/images/products/ipad_mini.jpg', hero_image='/static/images/hero/ipad_mini_hero.jpg',
                color_options=json.dumps(['Space Gray', 'Pink', 'Purple', 'Starlight']),
                storage_options=json.dumps(['64GB', '256GB']),
                specs=json.dumps({'chip': 'A15 Bionic', 'display': '8.3" Liquid Retina', 'connectivity': 'Wi-Fi + Cellular', 'storage': '64GB'}),
                chip_family='A15', connectivity='Wi-Fi + Cellular', release_year=2021),
        # --- Apple Watch older ---
        Product(name='Apple Watch Series 9', slug='apple-watch-series-9', category='watch',
                subtitle='Smarter. Brighter. Mightier.',
                description='S9 SiP, Always-On Retina display, blood oxygen sensing, ECG, temperature sensing.',
                price=399.00, monthly_price=16.62, months=24, is_new=False, is_featured=False,
                image='/static/images/products/watch_series_9.jpg', hero_image='/static/images/hero/watch_series_9_hero.jpg',
                color_options=json.dumps(['Midnight', 'Starlight', 'Silver', 'Red', 'Pink']),
                storage_options=json.dumps(['41mm', '45mm']),
                specs=json.dumps({'chip': 'S9 SiP', 'display': 'Always-On Retina', 'health': 'Blood oxygen, ECG, Temperature sensing'}),
                chip_family='S9', release_year=2023,
                slogan='Smarter. Brighter. Mightier.'),
        Product(name='Apple Watch SE', slug='apple-watch-se', category='watch',
                subtitle='A great deal to love.',
                description='S8 SiP, Crash Detection, heart rate notifications. A smartwatch for everyone.',
                price=249.00, monthly_price=10.37, months=24, is_new=False, is_featured=False,
                image='/static/images/products/watch_se.jpg', hero_image='/static/images/hero/watch_se_hero.jpg',
                color_options=json.dumps(['Midnight', 'Starlight', 'Silver']),
                storage_options=json.dumps(['40mm', '44mm']),
                specs=json.dumps({'chip': 'S8 SiP', 'display': 'Retina', 'health': 'Heart rate, Crash Detection'}),
                chip_family='S8', release_year=2022),
        # --- Apple TV 4K ---
        Product(name='Apple TV 4K', slug='apple-tv-4k', category='tv',
                subtitle='The Icons of icons.',
                description='A15 Bionic chip powers Apple TV 4K. 128GB storage. Experience Dolby Atmos and Dolby Vision. Siri Remote with Touch-enabled clickpad, built-in Find My, and USB-C charging.',
                price=129.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/apple_tv.jpg', hero_image='/static/images/hero/apple_tv_hero.jpg',
                color_options=json.dumps(['Black']),
                storage_options=json.dumps(['64GB', '128GB']),
                specs=json.dumps({'chip': 'A15 Bionic', 'storage': '128GB', 'connectivity': 'Wi-Fi 6, Gigabit Ethernet, Thread', 'siri_remote': 'Touch-enabled clickpad, Find My, USB-C charging', 'dimensions': 'Height: 31 mm, Width: 93 mm, Depth: 93 mm'}),
                chip_family='A15 Bionic', processor='A15 Bionic',
                weight='208 grams', release_year=2022),
        # --- HomePod mini ---
        Product(name='HomePod mini', slug='homepod-mini', category='homepod',
                subtitle='Icons Icons can do.',
                description='Room-filling sound in a compact design. Siri built in.',
                price=99.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/homepod_mini.jpg', hero_image='/static/images/hero/homepod_mini_hero.jpg',
                color_options=json.dumps(['White', 'Yellow', 'Orange', 'Blue', 'Space Gray']),
                storage_options=json.dumps([]),
                specs=json.dumps({'chip': 'S5', 'audio': 'Full-range driver, two passive radiators', 'features': 'Siri, Intercom, Find My'}),
                release_year=2023),
        # --- Apple Vision Pro ---
        Product(name='Apple Vision Pro', slug='apple-vision-pro', category='vision',
                subtitle='Welcome to the era of spatial computing.',
                description='Apple Vision Pro seamlessly blends digital content with your physical space. Weighing approximately 600 grams, it features a micro-OLED display system with 23 million pixels across two displays. Built-in apps include Safari, Photos, Music, Messages, and FaceTime. Available in the United States. Released February 2, 2024.',
                price=3499.00, monthly_price=145.79, months=24, is_new=True, is_featured=False,
                image='/static/images/products/vision_pro.jpg', hero_image='/static/images/hero/vision_pro_hero.jpg',
                color_options=json.dumps(['Silver']),
                storage_options=json.dumps(['256GB', '512GB', '1TB']),
                specs=json.dumps({
                    'chip': 'M2 + R1',
                    'display': 'Micro-OLED, 23 million pixels',
                    'audio': 'Spatial Audio',
                    'sensors': 'LiDAR, TrueDepth',
                    'builtin_apps': ['Safari', 'Photos', 'Music', 'Messages', 'FaceTime',
                                     'TV', 'Mindfulness', 'Keynote', 'Numbers', 'Pages'],
                    'weight': 'Approximately 600 grams',
                }),
                chip_family='M2 + R1', weight='approximately 600 grams',
                release_year=2024, release_date='February 2, 2024'),
        # --- Vision Pro Accessories ---
        Product(name='Apple Vision Pro Travel Case', slug='vision-pro-travel-case', category='accessories', subcategory='vision-pro-accessory',
                subtitle='Carry your Vision Pro with confidence.',
                description='Hard-shell Travel Case designed specifically for Apple Vision Pro.',
                price=199.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/vision_travel_case.jpg', hero_image='/static/images/hero/vision_travel_case_hero.jpg',
                color_options=json.dumps([]),
                storage_options=json.dumps([]),
                specs=json.dumps({'features': 'Hard-shell protective case, custom fit'})),
        Product(name='Apple Vision Pro Battery Pack', slug='vision-pro-battery', category='accessories', subcategory='vision-pro-accessory',
                subtitle='Extended Battery for Vision Pro.',
                description='External Battery pack for Apple Vision Pro providing up to 2 hours of additional use.',
                price=199.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/vision_battery.jpg', hero_image='/static/images/hero/vision_battery_hero.jpg',
                color_options=json.dumps([]),
                storage_options=json.dumps([]),
                specs=json.dumps({'features': 'Battery, 2 hours extended use'})),
        Product(name='Apple Vision Pro Light Seal', slug='vision-pro-light-seal', category='accessories', subcategory='vision-pro-accessory',
                subtitle='Custom fit for your face.',
                description='Light Seal replacement for Apple Vision Pro, available in multiple sizes.',
                price=199.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/vision_light_seal.jpg', hero_image='/static/images/hero/vision_light_seal_hero.jpg',
                color_options=json.dumps([]),
                storage_options=json.dumps([]),
                specs=json.dumps({'features': 'Light Seal, multiple sizes'})),
        # --- AirPods 3rd gen variants ---
        Product(name='AirPods 3rd generation (Lightning)', slug='airpods-3-lightning', category='airpods',
                subtitle='All-new design. Spatial Audio.',
                description='AirPods 3rd generation with Lightning charging case. Spatial Audio, Adaptive EQ, sweat and water resistant.',
                price=169.00, monthly_price=7.04, months=24, is_new=False, is_featured=False,
                image='/static/images/products/airpods_3.jpg', hero_image='/static/images/hero/airpods_3_hero.jpg',
                color_options=json.dumps(['White']),
                storage_options=json.dumps([]),
                specs=json.dumps({'chip': 'H1', 'audio': 'Spatial Audio, Adaptive EQ', 'charging': 'Lightning charging case'})),
        Product(name='AirPods 3rd generation (MagSafe)', slug='airpods-3-magsafe', category='airpods',
                subtitle='All-new design. Spatial Audio.',
                description='AirPods 3rd generation with MagSafe charging case. Spatial Audio, Adaptive EQ, sweat and water resistant.',
                price=179.00, monthly_price=7.45, months=24, is_new=False, is_featured=False,
                image='/static/images/products/airpods_3_magsafe.jpg', hero_image='/static/images/hero/airpods_3_magsafe_hero.jpg',
                color_options=json.dumps(['White']),
                storage_options=json.dumps([]),
                specs=json.dumps({'chip': 'H1', 'audio': 'Spatial Audio, Adaptive EQ', 'charging': 'MagSafe charging case'})),
        # --- Smart Folio for iPad ---
        Product(name='Smart Folio for iPad Air 11-inch', slug='smart-folio-for-ipad-air-11-inch', category='accessories', subcategory='ipad-accessory',
                subtitle='A Smart Folio for every iPad Air.',
                description='Slim, lightweight Smart Folio for iPad Air 11-inch. Automatically wakes and sleeps your iPad. Available in multiple colors.',
                price=79.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/smart_folio.jpg', hero_image='/static/images/hero/smart_folio_hero.jpg',
                color_options=json.dumps(['Charcoal Gray', 'Denim', 'Sage', 'Purple']),
                storage_options=json.dumps([]),
                specs=json.dumps({'features': 'Auto wake/sleep, foldable stand, magnetic attachment'})),
        Product(name='Smart Folio for iPad Pro 13-inch M4', slug='smart-folio-for-ipad-pro-13-inch-m4', category='accessories', subcategory='ipad-accessory',
                subtitle='Designed for iPad Pro.',
                description='Smart Folio for iPad Pro 13-inch (M4). Two viewing angles, auto wake/sleep.',
                price=99.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/smart_folio_pro.jpg', hero_image='/static/images/hero/smart_folio_pro_hero.jpg',
                color_options=json.dumps(['Black', 'Denim', 'Sage']),
                storage_options=json.dumps([]),
                specs=json.dumps({'features': 'Auto wake/sleep, two viewing positions, magnetic attachment'}),
                pickup_available=True),
        Product(name='Smart Folio for iPad Pro 11-inch M4', slug='smart-folio-for-ipad-pro-11-inch-m4', category='accessories', subcategory='ipad-accessory',
                subtitle='Designed for iPad Pro.',
                description='Smart Folio for iPad Pro 11-inch (M4). Slim and lightweight.',
                price=79.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/smart_folio_pro_11.jpg', hero_image='/static/images/hero/smart_folio_pro_11_hero.jpg',
                color_options=json.dumps(['Black', 'Denim', 'Sage']),
                storage_options=json.dumps([]),
                specs=json.dumps({'features': 'Auto wake/sleep, magnetic attachment'})),
        # ============================================================
        # Additional catalogue (expansion to 150+ products)
        # ============================================================
        # --- iPhone 16 series ---
        Product(name='iPhone 16 Pro', slug='iphone-16-pro', category='iphone',
                subtitle='Built for Apple Intelligence.',
                description='A18 Pro chip, 6.3-inch Super Retina XDR with ProMotion, 48MP Fusion camera and 5x Tetraprism telephoto, Camera Control button.',
                price=999.00, monthly_price=41.62, months=24, is_new=False, is_featured=False,
                image='/static/images/products/iphone_16_pro.jpg', hero_image='/static/images/hero/iphone_16_pro_hero.jpg',
                color_options=json.dumps(['Black Titanium', 'White Titanium', 'Natural Titanium', 'Desert Titanium']),
                storage_options=json.dumps(['128GB', '256GB', '512GB', '1TB']),
                specs=json.dumps({'chip': 'A18 Pro', 'display': '6.3" Super Retina XDR ProMotion', 'camera': '48MP Fusion + 48MP Ultra Wide + 12MP 5x Telephoto', 'battery': 'Up to 27 hours video playback'}),
                chip_family='A18 Pro', release_year=2024, release_date='September 20, 2024'),
        Product(name='iPhone 16 Pro Max', slug='iphone-16-pro-max', category='iphone',
                subtitle='So much Pro. So much Max.',
                description='6.9-inch Super Retina XDR display, A18 Pro chip, and the longest battery life ever in iPhone.',
                price=1199.00, monthly_price=49.95, months=24, is_new=False, is_featured=False,
                image='/static/images/products/iphone_16_pro_max.jpg', hero_image='/static/images/hero/iphone_16_pro_max_hero.jpg',
                color_options=json.dumps(['Black Titanium', 'White Titanium', 'Natural Titanium', 'Desert Titanium']),
                storage_options=json.dumps(['256GB', '512GB', '1TB']),
                specs=json.dumps({'chip': 'A18 Pro', 'display': '6.9" Super Retina XDR ProMotion', 'camera': '48MP Fusion + 48MP Ultra Wide + 12MP 5x Telephoto', 'battery': 'Up to 33 hours video playback'}),
                chip_family='A18 Pro', release_year=2024, release_date='September 20, 2024'),
        Product(name='iPhone 16', slug='iphone-16', category='iphone',
                subtitle='Hello, Apple Intelligence.',
                description='A18 chip, 48MP Fusion camera, Camera Control, and 6.1-inch Super Retina XDR display.',
                price=799.00, monthly_price=33.29, months=24, is_new=False, is_featured=False,
                image='/static/images/products/iphone_16.jpg', hero_image='/static/images/hero/iphone_16_hero.jpg',
                color_options=json.dumps(['Ultramarine', 'Teal', 'Pink', 'White', 'Black']),
                storage_options=json.dumps(['128GB', '256GB', '512GB']),
                specs=json.dumps({'chip': 'A18', 'display': '6.1" Super Retina XDR', 'camera': '48MP Fusion + 12MP Ultra Wide', 'battery': 'Up to 22 hours video playback'}),
                chip_family='A18', release_year=2024, release_date='September 20, 2024'),
        Product(name='iPhone 16 Plus', slug='iphone-16-plus', category='iphone',
                subtitle='Big screen. Big battery. Big deal.',
                description='6.7-inch Super Retina XDR display, A18 chip, and incredible battery life.',
                price=899.00, monthly_price=37.45, months=24, is_new=False, is_featured=False,
                image='/static/images/products/iphone_16_plus.jpg', hero_image='/static/images/hero/iphone_16_plus_hero.jpg',
                color_options=json.dumps(['Ultramarine', 'Teal', 'Pink', 'White', 'Black']),
                storage_options=json.dumps(['128GB', '256GB', '512GB']),
                specs=json.dumps({'chip': 'A18', 'display': '6.7" Super Retina XDR', 'camera': '48MP Fusion + 12MP Ultra Wide', 'battery': 'Up to 27 hours video playback'}),
                chip_family='A18', release_year=2024),
        Product(name='iPhone 15', slug='iphone-15', category='iphone',
                subtitle='Newphoria.',
                description='Dynamic Island, 48MP Main camera with 2x Telephoto, USB-C, A16 Bionic chip.',
                price=699.00, monthly_price=29.12, months=24, is_new=False, is_featured=False,
                image='/static/images/products/iphone_15.jpg', hero_image='/static/images/hero/iphone_15_hero.jpg',
                color_options=json.dumps(['Pink', 'Yellow', 'Green', 'Blue', 'Black']),
                storage_options=json.dumps(['128GB', '256GB', '512GB']),
                specs=json.dumps({'chip': 'A16 Bionic', 'display': '6.1" Super Retina XDR', 'camera': '48MP Main + 12MP Ultra Wide'}),
                chip_family='A16', release_year=2023, release_date='September 22, 2023'),
        Product(name='iPhone 15 Plus', slug='iphone-15-plus', category='iphone',
                subtitle='Newphoria.',
                description='6.7-inch Super Retina XDR display, Dynamic Island, USB-C, A16 Bionic chip.',
                price=799.00, monthly_price=33.29, months=24, is_new=False, is_featured=False,
                image='/static/images/products/iphone_15_plus.jpg', hero_image='/static/images/hero/iphone_15_plus_hero.jpg',
                color_options=json.dumps(['Pink', 'Yellow', 'Green', 'Blue', 'Black']),
                storage_options=json.dumps(['128GB', '256GB', '512GB']),
                specs=json.dumps({'chip': 'A16 Bionic', 'display': '6.7" Super Retina XDR'}),
                chip_family='A16', release_year=2023),
        Product(name='iPhone SE (3rd generation)', slug='iphone-se-3', category='iphone',
                subtitle='Serious power. Serious value.',
                description='A15 Bionic chip, 4.7-inch Retina HD display, Touch ID, single 12MP camera. The most affordable iPhone with 5G.',
                price=429.00, monthly_price=17.87, months=24, is_new=False, is_featured=False,
                image='/static/images/products/iphone_se_3.jpg', hero_image='/static/images/hero/iphone_se_3_hero.jpg',
                color_options=json.dumps(['Midnight', 'Starlight', 'Red']),
                storage_options=json.dumps(['64GB', '128GB', '256GB']),
                specs=json.dumps({'chip': 'A15 Bionic', 'display': '4.7" Retina HD', 'camera': '12MP Wide', 'connectivity': '5G'}),
                chip_family='A15', release_year=2022, release_date='March 18, 2022'),
        Product(name='iPhone 13', slug='iphone-13', category='iphone',
                subtitle='Your new superpower.',
                description='A15 Bionic chip, advanced dual-camera system, 6.1-inch Super Retina XDR display.',
                price=599.00, monthly_price=24.95, months=24, is_new=False, is_featured=False,
                image='/static/images/products/iphone_13.jpg', hero_image='/static/images/hero/iphone_13_hero.jpg',
                color_options=json.dumps(['Midnight', 'Starlight', 'Blue', 'Pink', 'Green', 'Red']),
                storage_options=json.dumps(['128GB', '256GB', '512GB']),
                specs=json.dumps({'chip': 'A15 Bionic', 'display': '6.1" Super Retina XDR', 'camera': '12MP dual camera'}),
                chip_family='A15', release_year=2021),
        Product(name='iPhone 13 mini', slug='iphone-13-mini', category='iphone',
                subtitle='Small wonder.',
                description='5.4-inch Super Retina XDR display, A15 Bionic chip, dual-camera system.',
                price=599.00, monthly_price=24.95, months=24, is_new=False, is_featured=False,
                image='/static/images/products/iphone_13_mini.jpg', hero_image='/static/images/hero/iphone_13_mini_hero.jpg',
                color_options=json.dumps(['Midnight', 'Starlight', 'Blue', 'Pink', 'Green', 'Red']),
                storage_options=json.dumps(['128GB', '256GB', '512GB']),
                specs=json.dumps({'chip': 'A15 Bionic', 'display': '5.4" Super Retina XDR'}),
                chip_family='A15', release_year=2021),
        Product(name='iPhone 12', slug='iphone-12', category='iphone',
                subtitle='Blast past fast.',
                description='A14 Bionic chip, 5G, OLED Super Retina XDR display, Ceramic Shield front.',
                price=499.00, monthly_price=20.79, months=24, is_new=False, is_featured=False,
                image='/static/images/products/iphone_12.jpg', hero_image='/static/images/hero/iphone_12_hero.jpg',
                color_options=json.dumps(['Black', 'White', 'Red', 'Green', 'Blue', 'Purple']),
                storage_options=json.dumps(['64GB', '128GB', '256GB']),
                specs=json.dumps({'chip': 'A14 Bionic', 'display': '6.1" Super Retina XDR', 'connectivity': '5G'}),
                chip_family='A14', release_year=2020),
        # --- Mac expansion ---
        Product(name='MacBook Pro 14-inch M4', slug='macbook-pro-14-inch-m4', category='mac', subcategory='macbook-pro',
                subtitle='A work of smart.',
                description='M4 chip, 14.2-inch Liquid Retina XDR display, 16GB unified memory, 512GB SSD, up to 24 hours of battery life.',
                price=1599.00, monthly_price=66.62, months=24, is_new=False, is_featured=False,
                image='/static/images/products/macbook_pro_14_m4.jpg', hero_image='/static/images/hero/macbook_pro_14_m4_hero.jpg',
                color_options=json.dumps(['Space Black', 'Silver']),
                storage_options=json.dumps(['512GB', '1TB', '2TB']),
                specs=json.dumps({'chip': 'M4', 'display': '14.2" Liquid Retina XDR', 'memory': '16GB / 24GB / 32GB unified memory', 'battery': 'Up to 24 hours'}),
                chip_family='M4', ram=16, ssd=512, screen_size=14.2, release_year=2024,
                release_date='November 8, 2024'),
        Product(name='MacBook Pro 14-inch M4 Pro', slug='macbook-pro-14-inch-m4-pro', category='mac', subcategory='macbook-pro',
                subtitle='Built for Apple Intelligence.',
                description='M4 Pro chip with up to 14-core CPU and 20-core GPU, 24GB unified memory, 512GB SSD.',
                price=1999.00, monthly_price=83.29, months=24, is_new=False, is_featured=False,
                image='/static/images/products/macbook_pro_14_m4_pro.jpg', hero_image='/static/images/hero/macbook_pro_14_m4_pro_hero.jpg',
                color_options=json.dumps(['Space Black', 'Silver']),
                storage_options=json.dumps(['512GB', '1TB', '2TB', '4TB']),
                specs=json.dumps({'chip': 'M4 Pro', 'cpu': '12-core or 14-core CPU', 'gpu': '16-core or 20-core GPU', 'memory': '24GB / 48GB unified memory'}),
                chip_family='M4 Pro', ram=24, ssd=512, cpu_cores=14, gpu_cores=20, screen_size=14.2, release_year=2024),
        Product(name='MacBook Pro 16-inch M4 Pro', slug='macbook-pro-16-inch-m4-pro', category='mac', subcategory='macbook-pro',
                subtitle='Outrageously powerful.',
                description='M4 Pro chip, 16.2-inch Liquid Retina XDR display, up to 22 hours of battery life.',
                price=2499.00, monthly_price=104.12, months=24, is_new=False, is_featured=False,
                image='/static/images/products/macbook_pro_16_m4_pro.jpg', hero_image='/static/images/hero/macbook_pro_16_m4_pro_hero.jpg',
                color_options=json.dumps(['Space Black', 'Silver']),
                storage_options=json.dumps(['512GB', '1TB', '2TB', '4TB']),
                specs=json.dumps({'chip': 'M4 Pro', 'display': '16.2" Liquid Retina XDR', 'memory': '24GB / 48GB unified memory', 'battery': 'Up to 22 hours'}),
                chip_family='M4 Pro', ram=24, ssd=512, screen_size=16.2, release_year=2024),
        Product(name='MacBook Pro 16-inch M4 Max', slug='macbook-pro-16-inch-m4-max', category='mac', subcategory='macbook-pro',
                subtitle='The most powerful MacBook Pro ever.',
                description='M4 Max chip with 16-core CPU and up to 40-core GPU, 36GB or 48GB unified memory, 1TB SSD.',
                price=3499.00, monthly_price=145.79, months=24, is_new=False, is_featured=False,
                image='/static/images/products/macbook_pro_16_m4_max.jpg', hero_image='/static/images/hero/macbook_pro_16_m4_max_hero.jpg',
                color_options=json.dumps(['Space Black', 'Silver']),
                storage_options=json.dumps(['1TB', '2TB', '4TB', '8TB']),
                specs=json.dumps({'chip': 'M4 Max', 'cpu': '16-core CPU', 'gpu': '40-core GPU', 'memory': '36GB / 48GB unified memory'}),
                chip_family='M4 Max', ram=48, ssd=1000, cpu_cores=16, gpu_cores=40, screen_size=16.2, release_year=2024),
        Product(name='MacBook Air 13-inch M2', slug='macbook-air-13-inch-m2', category='mac', subcategory='macbook-air',
                subtitle='Supercharged by M2.',
                description='M2 chip, 13.6-inch Liquid Retina display, 8GB unified memory, 256GB SSD, up to 18 hours of battery life.',
                price=999.00, monthly_price=41.62, months=24, is_new=False, is_featured=False,
                image='/static/images/products/macbook_air_13_m2.jpg', hero_image='/static/images/hero/macbook_air_13_m2_hero.jpg',
                color_options=json.dumps(['Midnight', 'Starlight', 'Space Gray', 'Silver']),
                storage_options=json.dumps(['256GB', '512GB', '1TB']),
                specs=json.dumps({'chip': 'M2', 'display': '13.6" Liquid Retina', 'memory': '8GB', 'battery': 'Up to 18 hours'}),
                chip_family='M2', ram=8, ssd=256, screen_size=13.6, release_year=2022),
        Product(name='MacBook Air 15-inch M2', slug='macbook-air-15-inch-m2', category='mac', subcategory='macbook-air',
                subtitle='Impressively big. Impossibly thin.',
                description='M2 chip, 15.3-inch Liquid Retina display.',
                price=1299.00, monthly_price=54.12, months=24, is_new=False, is_featured=False,
                image='/static/images/products/macbook_air_15_m2.jpg', hero_image='/static/images/hero/macbook_air_15_m2_hero.jpg',
                color_options=json.dumps(['Midnight', 'Starlight', 'Space Gray', 'Silver']),
                storage_options=json.dumps(['256GB', '512GB', '1TB']),
                specs=json.dumps({'chip': 'M2', 'display': '15.3" Liquid Retina', 'memory': '8GB', 'battery': 'Up to 18 hours'}),
                chip_family='M2', ram=8, screen_size=15.3, release_year=2023),
        Product(name='Mac mini M4', slug='mac-mini-m4', category='mac', subcategory='mac-mini',
                subtitle='Size: mini. Power: mighty.',
                description='M4 chip with 10-core CPU and 10-core GPU. 16GB unified memory, 256GB SSD. Compact 5x5-inch design.',
                price=599.00, monthly_price=24.95, months=24, is_new=False, is_featured=True,
                image='/static/images/products/mac_mini_m4.jpg', hero_image='/static/images/hero/mac_mini_m4_hero.jpg',
                color_options=json.dumps(['Silver']),
                storage_options=json.dumps(['256GB', '512GB', '1TB', '2TB']),
                specs=json.dumps({'chip': 'M4', 'cpu': '10-core CPU', 'gpu': '10-core GPU', 'memory': '16GB / 24GB / 32GB unified memory'}),
                chip_family='M4', ram=16, ssd=256, cpu_cores=10, gpu_cores=10, release_year=2024,
                release_date='November 8, 2024'),
        Product(name='Mac mini M4 Pro', slug='mac-mini-m4-pro', category='mac', subcategory='mac-mini',
                subtitle='Even mightier mini.',
                description='M4 Pro chip with 12-core CPU and 16-core GPU. 24GB unified memory, 512GB SSD.',
                price=1399.00, monthly_price=58.29, months=24, is_new=False, is_featured=False,
                image='/static/images/products/mac_mini_m4_pro.jpg', hero_image='/static/images/hero/mac_mini_m4_pro_hero.jpg',
                color_options=json.dumps(['Silver']),
                storage_options=json.dumps(['512GB', '1TB', '2TB', '4TB']),
                specs=json.dumps({'chip': 'M4 Pro', 'cpu': '12-core or 14-core CPU', 'gpu': '16-core or 20-core GPU', 'memory': '24GB / 48GB / 64GB'}),
                chip_family='M4 Pro', ram=24, ssd=512, cpu_cores=12, gpu_cores=16, release_year=2024),
        Product(name='Mac Studio M2 Max', slug='mac-studio-m2-max', category='mac', subcategory='mac-studio',
                subtitle='Empowers pros to push the limits.',
                description='M2 Max chip with 12-core CPU and 30-core GPU, 32GB unified memory, 512GB SSD.',
                price=1999.00, monthly_price=83.29, months=24, is_new=False, is_featured=False,
                image='/static/images/products/mac_studio_m2_max.jpg', hero_image='/static/images/hero/mac_studio_m2_max_hero.jpg',
                color_options=json.dumps(['Silver']),
                storage_options=json.dumps(['512GB', '1TB', '2TB', '4TB', '8TB']),
                specs=json.dumps({'chip': 'M2 Max', 'cpu': '12-core CPU', 'gpu': '30-core or 38-core GPU', 'memory': '32GB / 64GB / 96GB'}),
                chip_family='M2 Max', ram=32, ssd=512, cpu_cores=12, gpu_cores=30, release_year=2023),
        Product(name='Mac Studio M2 Ultra', slug='mac-studio-m2-ultra', category='mac', subcategory='mac-studio',
                subtitle='M2 Ultra. Ultra performer.',
                description='M2 Ultra chip with 24-core CPU and 60-core GPU, 64GB unified memory, 1TB SSD.',
                price=3999.00, monthly_price=166.62, months=24, is_new=False, is_featured=False,
                image='/static/images/products/mac_studio_m2_ultra.jpg', hero_image='/static/images/hero/mac_studio_m2_ultra_hero.jpg',
                color_options=json.dumps(['Silver']),
                storage_options=json.dumps(['1TB', '2TB', '4TB', '8TB']),
                specs=json.dumps({'chip': 'M2 Ultra', 'cpu': '24-core CPU', 'gpu': '60-core or 76-core GPU', 'memory': '64GB / 128GB / 192GB'}),
                chip_family='M2 Ultra', ram=64, ssd=1000, cpu_cores=24, gpu_cores=60, release_year=2023),
        Product(name='Mac Pro Tower', slug='mac-pro-tower', category='mac', subcategory='mac-pro',
                subtitle='Crafted for pros.',
                description='M2 Ultra chip, 64GB unified memory, 1TB SSD, six PCIe expansion slots. Tower enclosure.',
                price=6999.00, monthly_price=291.62, months=24, is_new=False, is_featured=False,
                image='/static/images/products/mac_pro_tower.jpg', hero_image='/static/images/hero/mac_pro_tower_hero.jpg',
                color_options=json.dumps(['Silver']),
                storage_options=json.dumps(['1TB', '2TB', '4TB', '8TB']),
                specs=json.dumps({'chip': 'M2 Ultra', 'memory': '64GB / 128GB / 192GB', 'expansion': '6 PCIe Gen 4 slots'}),
                chip_family='M2 Ultra', ram=64, ssd=1000, release_year=2023),
        Product(name='Mac Pro Rack', slug='mac-pro-rack', category='mac', subcategory='mac-pro',
                subtitle='Rack-mounted Pro.',
                description='M2 Ultra chip, rack-mountable enclosure for studio installations.',
                price=7499.00, monthly_price=312.45, months=24, is_new=False, is_featured=False,
                image='/static/images/products/mac_pro_rack.jpg', hero_image='/static/images/hero/mac_pro_rack_hero.jpg',
                color_options=json.dumps(['Silver']),
                storage_options=json.dumps(['1TB', '2TB', '4TB', '8TB']),
                specs=json.dumps({'chip': 'M2 Ultra', 'form_factor': '4U rack mount'}),
                chip_family='M2 Ultra', release_year=2023),
        Product(name='iMac 24-inch M4', slug='imac-24-inch-m4', category='mac', subcategory='imac',
                subtitle='Wonder full.',
                description='M4 chip, 24-inch 4.5K Retina display, 16GB unified memory, 256GB SSD. Seven vibrant colors.',
                price=1299.00, monthly_price=54.12, months=24, is_new=False, is_featured=True,
                image='/static/images/products/imac_m4.jpg', hero_image='/static/images/hero/imac_m4_hero.jpg',
                color_options=json.dumps(['Blue', 'Green', 'Pink', 'Silver', 'Yellow', 'Orange', 'Purple']),
                storage_options=json.dumps(['256GB', '512GB', '1TB', '2TB']),
                specs=json.dumps({'chip': 'M4', 'display': '24" 4.5K Retina', 'memory': '16GB / 24GB / 32GB'}),
                chip_family='M4', ram=16, screen_size=24.0, release_year=2024,
                release_date='November 8, 2024'),
        # --- iPad expansion ---
        Product(name='iPad Air 13-inch M4', slug='ipad-air-13-inch-m4', category='ipad', subcategory='ipad-air',
                subtitle='Big air. Big possibilities.',
                description='13-inch Liquid Retina display, M4 chip, Apple Pencil Pro support.',
                price=799.00, monthly_price=33.29, months=24, is_new=False, is_featured=False,
                image='/static/images/products/ipad_air_13_m4.jpg', hero_image='/static/images/hero/ipad_air_13_m4_hero.jpg',
                color_options=json.dumps(['Space Gray', 'Blue', 'Purple', 'Starlight']),
                storage_options=json.dumps(['128GB', '256GB', '512GB', '1TB']),
                specs=json.dumps({'chip': 'M4', 'display': '13" Liquid Retina', 'camera': '12MP Wide'}),
                chip_family='M4', screen_size=13.0, release_year=2024),
        Product(name='iPad Air 11-inch M4', slug='ipad-air-11-inch-m4', category='ipad', subcategory='ipad-air',
                subtitle='Now supercharged by M4.',
                description='11-inch Liquid Retina display, M4 chip.',
                price=599.00, monthly_price=24.95, months=24, is_new=False, is_featured=False,
                image='/static/images/products/ipad_air_11_m4.jpg', hero_image='/static/images/hero/ipad_air_11_m4_hero.jpg',
                color_options=json.dumps(['Space Gray', 'Blue', 'Purple', 'Starlight']),
                storage_options=json.dumps(['128GB', '256GB', '512GB', '1TB']),
                specs=json.dumps({'chip': 'M4', 'display': '11" Liquid Retina', 'camera': '12MP Wide'}),
                chip_family='M4', screen_size=11.0, release_year=2024),
        Product(name='iPad (A16)', slug='ipad-a16', category='ipad', subcategory='ipad',
                subtitle='Delightfully capable.',
                description='A16 chip, 11-inch Liquid Retina display. Perfect for everyday tasks.',
                price=349.00, monthly_price=14.54, months=24, is_new=False, is_featured=False,
                image='/static/images/products/ipad_a16.jpg', hero_image='/static/images/hero/ipad_a16_hero.jpg',
                color_options=json.dumps(['Blue', 'Pink', 'Yellow', 'Silver']),
                storage_options=json.dumps(['128GB', '256GB', '512GB']),
                specs=json.dumps({'chip': 'A16', 'display': '11" Liquid Retina'}),
                chip_family='A16', screen_size=11.0, release_year=2025),
        Product(name='iPad 9th generation', slug='ipad-9', category='ipad', subcategory='ipad',
                subtitle='Just the right amount of everything.',
                description='10.2-inch Retina display, A13 Bionic chip, Touch ID. Great value iPad.',
                price=329.00, monthly_price=13.71, months=24, is_new=False, is_featured=False,
                image='/static/images/products/ipad_9.jpg', hero_image='/static/images/hero/ipad_9_hero.jpg',
                color_options=json.dumps(['Space Gray', 'Silver']),
                storage_options=json.dumps(['64GB', '256GB']),
                specs=json.dumps({'chip': 'A13 Bionic', 'display': '10.2" Retina'}),
                chip_family='A13', release_year=2021),
        Product(name='iPad mini 6', slug='ipad-mini-6', category='ipad', subcategory='ipad-mini',
                subtitle='Mega power. Mini-sized.',
                description='A15 Bionic chip, 8.3-inch Liquid Retina display, Apple Pencil (2nd gen) support.',
                price=499.00, monthly_price=20.79, months=24, is_new=False, is_featured=False,
                image='/static/images/products/ipad_mini_6.jpg', hero_image='/static/images/hero/ipad_mini_6_hero.jpg',
                color_options=json.dumps(['Space Gray', 'Pink', 'Purple', 'Starlight']),
                storage_options=json.dumps(['64GB', '256GB']),
                specs=json.dumps({'chip': 'A15 Bionic', 'display': '8.3" Liquid Retina'}),
                chip_family='A15', release_year=2021),
        # --- Apple Watch expansion ---
        Product(name='Apple Watch Series 10', slug='apple-watch-series-10', category='watch',
                subtitle='Thinstant classic.',
                description='S10 SiP, the thinnest Apple Watch ever, sleep apnea detection, faster charging.',
                price=399.00, monthly_price=16.62, months=24, is_new=False, is_featured=False,
                image='/static/images/products/watch_series_10.jpg', hero_image='/static/images/hero/watch_series_10_hero.jpg',
                color_options=json.dumps(['Jet Black', 'Rose Gold', 'Silver', 'Slate', 'Gold']),
                storage_options=json.dumps(['42mm', '46mm']),
                specs=json.dumps({'chip': 'S10 SiP', 'display': 'Always-On Retina LTPO3', 'health': 'Blood oxygen, ECG, Sleep apnea'}),
                chip_family='S10', release_year=2024, release_date='September 20, 2024'),
        Product(name='Apple Watch Ultra 2', slug='apple-watch-ultra-2', category='watch',
                subtitle='Adventure awaits.',
                description='49mm titanium case, S9 SiP, dual-frequency GPS, up to 36 hours battery (72 in low power).',
                price=799.00, monthly_price=33.29, months=24, is_new=False, is_featured=False,
                image='/static/images/products/watch_ultra_2.jpg', hero_image='/static/images/hero/watch_ultra_2_hero.jpg',
                color_options=json.dumps(['Natural Titanium', 'Black Titanium']),
                storage_options=json.dumps(['49mm']),
                specs=json.dumps({'chip': 'S9 SiP', 'display': '49mm Always-On Retina', 'battery': 'Up to 36 hours'}),
                chip_family='S9', release_year=2023),
        Product(name='Apple Watch SE (2nd generation)', slug='apple-watch-se-2', category='watch',
                subtitle='A great deal to love.',
                description='S8 SiP, Crash Detection, fitness tracking. The most affordable Apple Watch.',
                price=249.00, monthly_price=10.37, months=24, is_new=False, is_featured=False,
                image='/static/images/products/watch_se_2.jpg', hero_image='/static/images/hero/watch_se_2_hero.jpg',
                color_options=json.dumps(['Midnight', 'Starlight', 'Silver']),
                storage_options=json.dumps(['40mm', '44mm']),
                specs=json.dumps({'chip': 'S8 SiP', 'display': 'Retina'}),
                chip_family='S8', release_year=2022),
        Product(name='Apple Watch Series 8', slug='apple-watch-series-8', category='watch',
                subtitle='A healthy leap ahead.',
                description='S8 SiP, temperature sensing, Crash Detection.',
                price=399.00, monthly_price=16.62, months=24, is_new=False, is_featured=False,
                image='/static/images/products/watch_series_8.jpg', hero_image='/static/images/hero/watch_series_8_hero.jpg',
                color_options=json.dumps(['Midnight', 'Starlight', 'Silver', 'Red']),
                storage_options=json.dumps(['41mm', '45mm']),
                specs=json.dumps({'chip': 'S8 SiP', 'health': 'Temperature sensing, ECG, Blood oxygen'}),
                chip_family='S8', release_year=2022),
        Product(name='Apple Watch Hermès Series 10', slug='apple-watch-hermes-series-10', category='watch',
                subtitle='A timepiece. Beyond.',
                description='Series 10 with an exclusive Hermès leather band and dial.',
                price=1249.00, monthly_price=52.04, months=24, is_new=False, is_featured=False,
                image='/static/images/products/watch_hermes.jpg', hero_image='/static/images/hero/watch_hermes_hero.jpg',
                color_options=json.dumps(['Silver Stainless Steel', 'Space Black Stainless Steel', 'Gold Stainless Steel']),
                storage_options=json.dumps(['42mm', '46mm']),
                specs=json.dumps({'chip': 'S10 SiP', 'bands': 'Hermès exclusive bands'}),
                chip_family='S10', release_year=2024),
        # --- AirPods expansion ---
        Product(name='AirPods Pro (2nd generation) USB-C', slug='airpods-pro-2-usb-c', category='airpods',
                subtitle='Adaptive Audio. Now playing.',
                description='H2 chip, Active Noise Cancellation, Adaptive Audio, USB-C MagSafe charging case.',
                price=249.00, monthly_price=10.37, months=24, is_new=False, is_featured=False,
                image='/static/images/products/airpods_pro_2_usbc.jpg', hero_image='/static/images/hero/airpods_pro_2_usbc_hero.jpg',
                color_options=json.dumps(['White']),
                storage_options=json.dumps([]),
                specs=json.dumps({'chip': 'H2', 'anc': 'Active Noise Cancellation', 'charging': 'USB-C, MagSafe, Lightning, Wireless'}),
                release_year=2023),
        Product(name='AirPods 4 with Active Noise Cancellation', slug='airpods-4-anc', category='airpods',
                subtitle='Iconic. With ANC.',
                description='Open-ear design with Active Noise Cancellation, Adaptive Audio, and USB-C charging case.',
                price=179.00, monthly_price=7.45, months=24, is_new=False, is_featured=False,
                image='/static/images/products/airpods_4_anc.jpg', hero_image='/static/images/hero/airpods_4_anc_hero.jpg',
                color_options=json.dumps(['White']),
                storage_options=json.dumps([]),
                specs=json.dumps({'chip': 'H2', 'anc': 'Active Noise Cancellation', 'battery': 'Up to 5 hours (30 with case)'}),
                release_year=2024),
        # --- Apple TV / HomePod expansion ---
        Product(name='HomePod (2nd generation)', slug='homepod-2', category='homepod',
                subtitle='Profound sound.',
                description='Full-size HomePod with S7 chip, room sensing, and Spatial Audio.',
                price=299.00, monthly_price=12.45, months=24, is_new=False, is_featured=False,
                image='/static/images/products/homepod_2.jpg', hero_image='/static/images/hero/homepod_2_hero.jpg',
                color_options=json.dumps(['Midnight', 'White']),
                storage_options=json.dumps([]),
                specs=json.dumps({'chip': 'S7', 'audio': 'High-excursion woofer + five tweeters, Spatial Audio'}),
                release_year=2023),
        # --- Studio Display, Pro Display XDR ---
        Product(name='Studio Display', slug='studio-display', category='accessories', subcategory='display',
                subtitle='A sight to be bold.',
                description='27-inch 5K Retina display with 600 nits brightness, A13 chip, 12MP Ultra Wide camera, six-speaker sound system.',
                price=1599.00, monthly_price=66.62, months=24, is_new=False, is_featured=False,
                image='/static/images/products/studio_display.jpg', hero_image='/static/images/hero/studio_display_hero.jpg',
                color_options=json.dumps(['Silver']),
                storage_options=json.dumps([]),
                specs=json.dumps({'display': '27" 5K Retina', 'chip': 'A13 Bionic', 'camera': '12MP Ultra Wide with Center Stage'}),
                screen_size=27.0, release_year=2022),
        Product(name='Pro Display XDR', slug='pro-display-xdr', category='accessories', subcategory='display',
                subtitle='Pro to the max.',
                description='32-inch 6K Retina XDR display with 1000 nits sustained brightness, P3 wide color, and Extreme Dynamic Range.',
                price=4999.00, monthly_price=208.29, months=24, is_new=False, is_featured=False,
                image='/static/images/products/pro_display_xdr.jpg', hero_image='/static/images/hero/pro_display_xdr_hero.jpg',
                color_options=json.dumps(['Silver']),
                storage_options=json.dumps([]),
                specs=json.dumps({'display': '32" 6K Retina XDR', 'brightness': '1000 nits sustained, 1600 peak', 'color': 'P3 wide color'}),
                screen_size=32.0, release_year=2019),
        # --- Beats audio (Apple-owned) ---
        Product(name='Beats Studio Pro', slug='beats-studio-pro', category='audio', subcategory='headphones',
                subtitle='Made to be heard.',
                description='Over-ear Beats Studio Pro with Active Noise Cancellation, Spatial Audio, and 40 hours battery.',
                price=349.00, monthly_price=14.54, months=24, is_new=False, is_featured=False,
                image='/static/images/products/beats_studio_pro.jpg', hero_image='/static/images/hero/beats_studio_pro_hero.jpg',
                color_options=json.dumps(['Black', 'Navy', 'Sandstone', 'Deep Brown']),
                storage_options=json.dumps([]),
                specs=json.dumps({'anc': 'Active Noise Cancellation', 'battery': 'Up to 40 hours'}),
                release_year=2023),
        Product(name='Beats Solo 4', slug='beats-solo-4', category='audio', subcategory='headphones',
                subtitle='Sound. Better.',
                description='On-ear Beats Solo 4 headphones with up to 50 hours battery life, USB-C, and lossless audio.',
                price=199.00, monthly_price=8.29, months=24, is_new=False, is_featured=False,
                image='/static/images/products/beats_solo_4.jpg', hero_image='/static/images/hero/beats_solo_4_hero.jpg',
                color_options=json.dumps(['Matte Black', 'Slate Blue', 'Cloud Pink']),
                storage_options=json.dumps([]),
                specs=json.dumps({'battery': 'Up to 50 hours', 'audio': 'Lossless via USB-C'}),
                release_year=2024),
        Product(name='Beats Studio Buds+', slug='beats-studio-buds-plus', category='audio', subcategory='earbuds',
                subtitle='Up the ante.',
                description='True wireless earbuds with Active Noise Cancellation, Transparency mode, IPX4, USB-C charging case.',
                price=169.00, monthly_price=7.04, months=24, is_new=False, is_featured=False,
                image='/static/images/products/beats_studio_buds_plus.jpg', hero_image='/static/images/hero/beats_studio_buds_plus_hero.jpg',
                color_options=json.dumps(['Black/Gold', 'Ivory', 'Transparent', 'Cosmic Pink']),
                storage_options=json.dumps([]),
                specs=json.dumps({'anc': 'Active Noise Cancellation', 'water_resistance': 'IPX4'}),
                release_year=2023),
        Product(name='Beats Fit Pro', slug='beats-fit-pro', category='audio', subcategory='earbuds',
                subtitle='Total custom fit.',
                description='True wireless earbuds with secure-fit wingtips, Active Noise Cancellation, Spatial Audio, Apple H1 chip.',
                price=199.00, monthly_price=8.29, months=24, is_new=False, is_featured=False,
                image='/static/images/products/beats_fit_pro.jpg', hero_image='/static/images/hero/beats_fit_pro_hero.jpg',
                color_options=json.dumps(['Black', 'White', 'Stone Purple', 'Sage Gray']),
                storage_options=json.dumps([]),
                specs=json.dumps({'chip': 'Apple H1', 'anc': 'Active Noise Cancellation'}),
                release_year=2021),
        Product(name='Beats Pill', slug='beats-pill', category='audio', subcategory='speaker',
                subtitle='Take the party.',
                description='Portable wireless speaker with up to 24 hours of playback and IP67 dust- and water-resistance.',
                price=149.00, monthly_price=6.21, months=24, is_new=False, is_featured=False,
                image='/static/images/products/beats_pill.jpg', hero_image='/static/images/hero/beats_pill_hero.jpg',
                color_options=json.dumps(['Matte Black', 'Statement Red', 'Champagne Gold']),
                storage_options=json.dumps([]),
                specs=json.dumps({'battery': 'Up to 24 hours', 'water_resistance': 'IP67'}),
                release_year=2024),
        # --- Accessories: chargers / cables / power ---
        Product(name='MagSafe Charger (1m)', slug='magsafe-charger-1m', category='accessories', subcategory='charger',
                subtitle='Wireless charging. Magnetic. Snap.',
                description='1-metre MagSafe wireless charger compatible with all MagSafe-enabled iPhones.',
                price=39.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/magsafe_charger.jpg', hero_image='/static/images/hero/magsafe_charger_hero.jpg',
                color_options=json.dumps(['White']),
                storage_options=json.dumps([]),
                specs=json.dumps({'features': 'MagSafe wireless charging, 15W max'})),
        Product(name='MagSafe Duo Charger', slug='magsafe-duo-charger', category='accessories', subcategory='charger',
                subtitle='Charge two. Fold flat.',
                description='Foldable MagSafe Duo Charger for iPhone and Apple Watch.',
                price=129.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/magsafe_duo.jpg', hero_image='/static/images/hero/magsafe_duo_hero.jpg',
                color_options=json.dumps(['White']),
                storage_options=json.dumps([]),
                specs=json.dumps({'features': 'MagSafe + Apple Watch wireless charging'})),
        Product(name='20W USB-C Power Adapter', slug='usb-c-power-adapter-20w', category='accessories', subcategory='charger',
                subtitle='Fast. Charge.',
                description='Apple 20W USB-C Power Adapter for fast charging compatible iPhones and iPads.',
                price=19.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/usb_c_20w.jpg', hero_image='/static/images/hero/usb_c_20w_hero.jpg',
                color_options=json.dumps(['White']),
                storage_options=json.dumps([]),
                specs=json.dumps({'power': '20W'})),
        Product(name='USB-C to Lightning Cable (1m)', slug='usb-c-lightning-cable-1m', category='accessories', subcategory='cable',
                subtitle='Connect, charge, sync.',
                description='1-meter USB-C to Lightning cable, supports fast charge.',
                price=19.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/usbc_lightning.jpg', hero_image='/static/images/hero/usbc_lightning_hero.jpg',
                color_options=json.dumps(['White']),
                storage_options=json.dumps([]),
                specs=json.dumps({'length': '1 metre'})),
        Product(name='USB-C Charge Cable (2m)', slug='usb-c-charge-cable-2m', category='accessories', subcategory='cable',
                subtitle='Charge and sync your Apple devices.',
                description='2-meter USB-C charge cable.',
                price=29.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/usbc_2m.jpg', hero_image='/static/images/hero/usbc_2m_hero.jpg',
                color_options=json.dumps(['White']),
                storage_options=json.dumps([]),
                specs=json.dumps({'length': '2 metre'})),
        Product(name='EarPods (USB-C)', slug='earpods-usb-c', category='accessories', subcategory='earbuds',
                subtitle='An iconic design, now with USB-C.',
                description='Wired EarPods with a USB-C connector. Includes inline remote and microphone.',
                price=19.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/earpods_usbc.jpg', hero_image='/static/images/hero/earpods_usbc_hero.jpg',
                color_options=json.dumps(['White']),
                storage_options=json.dumps([]),
                specs=json.dumps({'connector': 'USB-C'})),
        # --- Accessories: Mac peripherals ---
        Product(name='Magic Mouse (USB-C)', slug='magic-mouse-usb-c', category='accessories', subcategory='mac-accessory',
                subtitle='Multi-Touch surface. Now with USB-C.',
                description='Magic Mouse with rechargeable battery, Multi-Touch surface, USB-C charging.',
                price=99.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/magic_mouse.jpg', hero_image='/static/images/hero/magic_mouse_hero.jpg',
                color_options=json.dumps(['White', 'Black']),
                storage_options=json.dumps([]),
                specs=json.dumps({'features': 'Multi-Touch, USB-C charging'})),
        Product(name='Magic Trackpad (USB-C)', slug='magic-trackpad-usb-c', category='accessories', subcategory='mac-accessory',
                subtitle='Click. Swipe. Force.',
                description='Magic Trackpad with Force Touch, large Multi-Touch surface, USB-C charging.',
                price=129.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/magic_trackpad.jpg', hero_image='/static/images/hero/magic_trackpad_hero.jpg',
                color_options=json.dumps(['White', 'Black']),
                storage_options=json.dumps([]),
                specs=json.dumps({'features': 'Force Touch, Multi-Touch'})),
        Product(name='Magic Keyboard with Touch ID and Numeric Keypad', slug='magic-keyboard-touch-id-numeric', category='accessories', subcategory='mac-accessory',
                subtitle='Type, click, log in.',
                description='Full-size Magic Keyboard with Touch ID, numeric keypad, and USB-C charging.',
                price=199.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/magic_keyboard_touchid.jpg', hero_image='/static/images/hero/magic_keyboard_touchid_hero.jpg',
                color_options=json.dumps(['White', 'Black']),
                storage_options=json.dumps([]),
                specs=json.dumps({'features': 'Touch ID, numeric keypad, USB-C'})),
        Product(name='Apple TV 4K Remote', slug='apple-tv-remote', category='accessories', subcategory='tv-accessory',
                subtitle='Take control.',
                description='Replacement Siri Remote with Touch-enabled clickpad and USB-C charging.',
                price=59.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/apple_tv_remote.jpg', hero_image='/static/images/hero/apple_tv_remote_hero.jpg',
                color_options=json.dumps(['Silver']),
                storage_options=json.dumps([]),
                specs=json.dumps({'features': 'Siri, Touch-enabled clickpad, USB-C charging'})),
        Product(name='Polishing Cloth', slug='polishing-cloth', category='accessories', subcategory='care',
                subtitle='Soft, non-abrasive.',
                description='Made with soft, nonabrasive material that cleans any Apple display, including nano-texture glass.',
                price=19.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/polishing_cloth.jpg', hero_image='/static/images/hero/polishing_cloth_hero.jpg',
                color_options=json.dumps(['Gray']),
                storage_options=json.dumps([]),
                specs=json.dumps({'features': 'Safe on nano-texture glass'})),
        Product(name='World Travel Adapter Kit', slug='world-travel-adapter-kit', category='accessories', subcategory='charger',
                subtitle='Plug. Travel. Repeat.',
                description='Set of seven AC plugs with prongs that fit most outlets around the world.',
                price=29.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/travel_adapter_kit.jpg', hero_image='/static/images/hero/travel_adapter_kit_hero.jpg',
                color_options=json.dumps(['White']),
                storage_options=json.dumps([]),
                specs=json.dumps({'plugs': 'NA, JP, CN, UK, AU, EU, KR'})),
        # --- iPhone cases / accessories ---
        Product(name='iPhone 17 Pro Silicone Case with MagSafe', slug='iphone-17-pro-silicone-case', category='accessories', subcategory='iphone-case',
                subtitle='Snug. Stylish. Snap.',
                description='Silicone case designed for iPhone 17 Pro, with built-in magnets for MagSafe accessories.',
                price=49.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/iphone_17_pro_case.jpg', hero_image='/static/images/hero/iphone_17_pro_case_hero.jpg',
                color_options=json.dumps(['Black', 'Stone', 'Plum', 'Lake Green', 'Denim']),
                storage_options=json.dumps([]),
                specs=json.dumps({'compat': 'iPhone 17 Pro', 'features': 'MagSafe magnets, silicone'})),
        Product(name='iPhone 17 Clear Case with MagSafe', slug='iphone-17-clear-case', category='accessories', subcategory='iphone-case',
                subtitle='Show off your iPhone.',
                description='Clear case for iPhone 17 with MagSafe magnets.',
                price=49.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/iphone_17_clear_case.jpg', hero_image='/static/images/hero/iphone_17_clear_case_hero.jpg',
                color_options=json.dumps(['Clear']),
                storage_options=json.dumps([]),
                specs=json.dumps({'compat': 'iPhone 17', 'features': 'MagSafe magnets, clear polycarbonate'})),
        Product(name='iPhone FineWoven Wallet with MagSafe', slug='finewoven-wallet-magsafe', category='accessories', subcategory='iphone-case',
                subtitle='Card holder. Snap on.',
                description='MagSafe-compatible FineWoven wallet that attaches to the back of any MagSafe iPhone.',
                price=59.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/finewoven_wallet.jpg', hero_image='/static/images/hero/finewoven_wallet_hero.jpg',
                color_options=json.dumps(['Black', 'Mulberry', 'Taupe', 'Evergreen']),
                storage_options=json.dumps([]),
                specs=json.dumps({'features': 'FineWoven, MagSafe wallet, Find My support'})),
        # --- Apple Watch Bands ---
        Product(name='Sport Band (46mm)', slug='sport-band-46mm', category='accessories', subcategory='watch-band',
                subtitle='Light. Bouncy. Sport.',
                description='High-performance fluoroelastomer Sport Band for 46mm Apple Watch.',
                price=49.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/sport_band.jpg', hero_image='/static/images/hero/sport_band_hero.jpg',
                color_options=json.dumps(['Black', 'White', 'Plum', 'Lake Green', 'Stone Grey']),
                storage_options=json.dumps(['S/M', 'M/L']),
                specs=json.dumps({'compat': '42mm and 46mm Apple Watch'})),
        Product(name='Sport Loop (46mm)', slug='sport-loop-46mm', category='accessories', subcategory='watch-band',
                subtitle='Soft. Hook-and-loop.',
                description='Lightweight nylon Sport Loop with hook-and-loop fastener.',
                price=49.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/sport_loop.jpg', hero_image='/static/images/hero/sport_loop_hero.jpg',
                color_options=json.dumps(['Black', 'Beige', 'Lake Green', 'Plum']),
                storage_options=json.dumps([]),
                specs=json.dumps({'compat': '42mm and 46mm Apple Watch'})),
        Product(name='Milanese Loop (46mm)', slug='milanese-loop-46mm', category='accessories', subcategory='watch-band',
                subtitle='Mesh. Magnetic. Refined.',
                description='Custom-designed magnetic stainless steel mesh Milanese Loop.',
                price=99.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/milanese_loop.jpg', hero_image='/static/images/hero/milanese_loop_hero.jpg',
                color_options=json.dumps(['Silver', 'Graphite', 'Gold']),
                storage_options=json.dumps([]),
                specs=json.dumps({'material': 'Stainless steel mesh'})),
        Product(name='Ocean Band (49mm)', slug='ocean-band-49mm', category='accessories', subcategory='watch-band',
                subtitle='Built for high-speed water sports.',
                description='Ocean Band for Apple Watch Ultra, made from elastomer.',
                price=99.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/ocean_band.jpg', hero_image='/static/images/hero/ocean_band_hero.jpg',
                color_options=json.dumps(['White', 'Black', 'Blue', 'Orange']),
                storage_options=json.dumps([]),
                specs=json.dumps({'compat': 'Apple Watch Ultra (49mm)'})),
        Product(name='Trail Loop (49mm)', slug='trail-loop-49mm', category='accessories', subcategory='watch-band',
                subtitle='Lightweight, breathable.',
                description='Trail Loop for Apple Watch Ultra with thin profile and adjustable fit.',
                price=99.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/trail_loop.jpg', hero_image='/static/images/hero/trail_loop_hero.jpg',
                color_options=json.dumps(['Green/Gray', 'Blue/Black', 'Orange/Beige']),
                storage_options=json.dumps([]),
                specs=json.dumps({'compat': 'Apple Watch Ultra (49mm)'})),
        Product(name='Alpine Loop (49mm)', slug='alpine-loop-49mm', category='accessories', subcategory='watch-band',
                subtitle='Engineered for adventure.',
                description='Two-layer textile Alpine Loop for Apple Watch Ultra with G-hook closure.',
                price=99.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/alpine_loop.jpg', hero_image='/static/images/hero/alpine_loop_hero.jpg',
                color_options=json.dumps(['Green', 'Blue', 'Black', 'Ocean Blue']),
                storage_options=json.dumps([]),
                specs=json.dumps({'compat': 'Apple Watch Ultra (49mm)'})),
        # --- iPad Pencil / Case extras ---
        Product(name='Apple Pencil (1st generation)', slug='apple-pencil-1st-gen', category='accessories', subcategory='pencil',
                subtitle='Pixel-perfect precision.',
                description='Apple Pencil (1st generation) for iPad with Lightning connector.',
                price=99.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/apple_pencil_1.jpg', hero_image='/static/images/hero/apple_pencil_1_hero.jpg',
                color_options=json.dumps(['White']),
                storage_options=json.dumps([]),
                specs=json.dumps({'connector': 'Lightning'})),
        Product(name='Magic Keyboard for iPad Pro (M4)', slug='magic-keyboard-ipad-pro-m4', category='accessories', subcategory='ipad-accessory',
                subtitle='Floating cantilever. Now thinner.',
                description='Magic Keyboard built for iPad Pro (M4) with backlit keys, function row, and larger trackpad.',
                price=299.00, monthly_price=12.45, months=24, is_new=False, is_featured=False,
                image='/static/images/products/magic_keyboard_ipad_pro_m4.jpg', hero_image='/static/images/hero/magic_keyboard_ipad_pro_m4_hero.jpg',
                color_options=json.dumps(['White', 'Black']),
                storage_options=json.dumps([]),
                specs=json.dumps({'features': 'Backlit keys, function row, larger trackpad'})),
        Product(name='Smart Folio for iPad mini', slug='smart-folio-ipad-mini', category='accessories', subcategory='ipad-accessory',
                subtitle='Front and back. Sleek.',
                description='Slim Smart Folio for iPad mini, with auto wake/sleep and magnetic attachment.',
                price=59.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/smart_folio_mini.jpg', hero_image='/static/images/hero/smart_folio_mini_hero.jpg',
                color_options=json.dumps(['Charcoal Gray', 'Denim', 'Sage', 'Purple']),
                storage_options=json.dumps([]),
                specs=json.dumps({'compat': 'iPad mini', 'features': 'Auto wake/sleep, magnetic attachment'})),
        # --- iPhone trade-in ready older models ---
        Product(name='iPhone 12 mini', slug='iphone-12-mini', category='iphone',
                subtitle='Small wonder.',
                description='5.4-inch Super Retina XDR display, A14 Bionic chip, 5G.',
                price=399.00, monthly_price=16.62, months=24, is_new=False, is_featured=False,
                image='/static/images/products/iphone_12_mini.jpg', hero_image='/static/images/hero/iphone_12_mini_hero.jpg',
                color_options=json.dumps(['Black', 'White', 'Red', 'Green', 'Blue', 'Purple']),
                storage_options=json.dumps(['64GB', '128GB', '256GB']),
                specs=json.dumps({'chip': 'A14 Bionic', 'display': '5.4" Super Retina XDR'}),
                chip_family='A14', release_year=2020),
        Product(name='iPhone 11', slug='iphone-11', category='iphone',
                subtitle='Just the right amount of everything.',
                description='A13 Bionic chip, dual 12MP camera, 6.1-inch Liquid Retina HD display.',
                price=399.00, monthly_price=16.62, months=24, is_new=False, is_featured=False,
                image='/static/images/products/iphone_11.jpg', hero_image='/static/images/hero/iphone_11_hero.jpg',
                color_options=json.dumps(['Black', 'White', 'Red', 'Yellow', 'Purple', 'Green']),
                storage_options=json.dumps(['64GB', '128GB', '256GB']),
                specs=json.dumps({'chip': 'A13 Bionic', 'display': '6.1" Liquid Retina HD'}),
                chip_family='A13', release_year=2019),
        # --- AppleCare-style services as products (so they show in support browse) ---
        Product(name='AppleCare+ for iPhone (Monthly)', slug='applecare-iphone-monthly', category='accessories', subcategory='service',
                subtitle='Coverage when you need it most.',
                description='AppleCare+ for iPhone provides unlimited incidents of accidental damage protection, 24/7 priority access to Apple experts, and battery service coverage. Monthly billing.',
                price=9.99, monthly_price=9.99, months=24, is_new=False, is_featured=False,
                image='/static/images/products/applecare.jpg', hero_image='/static/images/hero/applecare_hero.jpg',
                color_options=json.dumps([]),
                storage_options=json.dumps([]),
                specs=json.dumps({'features': 'Accidental damage protection, 24/7 support, battery service'})),
        Product(name='AppleCare+ for Mac (Annual)', slug='applecare-mac-annual', category='accessories', subcategory='service',
                subtitle='Peace of mind for your Mac.',
                description='Three years of AppleCare+ coverage for Mac with unlimited incidents of accidental damage protection.',
                price=199.00, monthly_price=None, months=0, is_new=False, is_featured=False,
                image='/static/images/products/applecare_mac.jpg', hero_image='/static/images/hero/applecare_mac_hero.jpg',
                color_options=json.dumps([]),
                storage_options=json.dumps([]),
                specs=json.dumps({'features': '3-year coverage, accidental damage, 24/7 support'})),
    ]

    for p in products:
        db.session.add(p)
    db.session.commit()
    print(f"Seeded {len(products)} products")

    # --- Trade-In Values ---
    trade_in_values = [
        TradeInValue(device='iPhone 15 Pro Max', condition='good', value=650.00,
                     notes='Trade in your iPhone 15 Pro Max for credit toward a new iPhone.'),
        TradeInValue(device='iPhone 15 Pro', condition='good', value=570.00,
                     notes='Trade in your iPhone 15 Pro for credit toward a new iPhone.'),
        TradeInValue(device='iPhone 14 Pro Max', condition='good', value=500.00,
                     notes='Trade in your iPhone 14 Pro Max for credit toward a new iPhone.'),
        TradeInValue(device='iPhone 14 Pro', condition='good', value=430.00,
                     notes='Trade in your iPhone 14 Pro for credit toward a new iPhone.'),
        TradeInValue(device='iPhone 13 Pro Max', condition='good', value=440.00,
                     notes='Trade in your iPhone 13 Pro Max for credit toward a new iPhone.'),
        TradeInValue(device='iPhone 13 Pro', condition='good', value=370.00,
                     notes='Trade in your iPhone 13 Pro for credit toward a new iPhone.'),
        TradeInValue(device='iPhone 12 Pro Max', condition='good', value=300.00,
                     notes='Trade in your iPhone 12 Pro Max for credit toward a new iPhone.'),
        TradeInValue(device='iPhone 12 Pro', condition='good', value=250.00,
                     notes='Trade in your iPhone 12 Pro for credit toward a new iPhone.'),
        TradeInValue(device='iPhone 11 Pro Max', condition='good', value=230.00,
                     notes='Trade in your iPhone 11 Pro Max for credit toward a new iPhone.'),
        TradeInValue(device='iPhone 11 Pro', condition='good', value=200.00,
                     notes='Trade in your iPhone 11 Pro for credit toward a new iPhone.'),
        TradeInValue(device='iPhone 16 Pro Max', condition='good', value=750.00,
                     notes='Trade in your iPhone 16 Pro Max for credit toward a new iPhone.'),
        TradeInValue(device='iPhone 16 Pro', condition='good', value=650.00,
                     notes='Trade in your iPhone 16 Pro for credit toward a new iPhone.'),
        TradeInValue(device='iPhone 16 Plus', condition='good', value=470.00,
                     notes='Trade in your iPhone 16 Plus for credit toward a new iPhone.'),
        TradeInValue(device='iPhone 16', condition='good', value=420.00,
                     notes='Trade in your iPhone 16 for credit toward a new iPhone.'),
        TradeInValue(device='iPhone 15 Plus', condition='good', value=400.00,
                     notes='Trade in your iPhone 15 Plus for credit toward a new iPhone.'),
        TradeInValue(device='iPhone 15', condition='good', value=350.00,
                     notes='Trade in your iPhone 15 for credit toward a new iPhone.'),
        TradeInValue(device='iPhone 14 Plus', condition='good', value=330.00,
                     notes='Trade in your iPhone 14 Plus for credit toward a new iPhone.'),
        TradeInValue(device='iPhone 14', condition='good', value=290.00,
                     notes='Trade in your iPhone 14 for credit toward a new iPhone.'),
        TradeInValue(device='iPhone 13', condition='good', value=240.00,
                     notes='Trade in your iPhone 13 for credit toward a new iPhone.'),
        TradeInValue(device='iPhone 13 mini', condition='good', value=190.00,
                     notes='Trade in your iPhone 13 mini for credit toward a new iPhone.'),
        TradeInValue(device='iPhone 12', condition='good', value=170.00,
                     notes='Trade in your iPhone 12 for credit toward a new iPhone.'),
        TradeInValue(device='iPhone 12 mini', condition='good', value=130.00,
                     notes='Trade in your iPhone 12 mini for credit toward a new iPhone.'),
        TradeInValue(device='iPhone 11', condition='good', value=140.00,
                     notes='Trade in your iPhone 11 for credit toward a new iPhone.'),
        TradeInValue(device='iPhone XR', condition='good', value=80.00,
                     notes='Trade in your iPhone XR for credit toward a new iPhone.'),
        TradeInValue(device='iPhone XS Max', condition='good', value=100.00,
                     notes='Trade in your iPhone XS Max for credit toward a new iPhone.'),
        TradeInValue(device='iPhone XS', condition='good', value=80.00,
                     notes='Trade in your iPhone XS for credit toward a new iPhone.'),
        TradeInValue(device='iPhone X', condition='good', value=60.00,
                     notes='Trade in your iPhone X for credit toward a new iPhone.'),
        TradeInValue(device='iPhone 8 Plus', condition='good', value=40.00,
                     notes='Trade in your iPhone 8 Plus for credit toward a new iPhone.'),
        TradeInValue(device='iPhone 8', condition='good', value=30.00,
                     notes='Trade in your iPhone 8 for credit toward a new iPhone.'),
        TradeInValue(device='iPhone SE (3rd generation)', condition='good', value=120.00,
                     notes='Trade in your iPhone SE (3rd generation) for credit toward a new iPhone.'),
        TradeInValue(device='iPhone SE (2nd generation)', condition='good', value=70.00,
                     notes='Trade in your iPhone SE (2nd generation) for credit toward a new iPhone.'),
        # Mac variants
        TradeInValue(device='MacBook Pro 16-inch', condition='good', value=900.00,
                     notes='Trade in your MacBook Pro 16-inch for credit toward a new Mac.'),
        TradeInValue(device='MacBook Pro 14-inch', condition='good', value=700.00,
                     notes='Trade in your MacBook Pro 14-inch for credit toward a new Mac.'),
        TradeInValue(device='MacBook Pro 13-inch', condition='good', value=380.00,
                     notes='Trade in your MacBook Pro 13-inch for credit toward a new Mac.'),
        TradeInValue(device='MacBook Air M3', condition='good', value=560.00,
                     notes='Trade in your MacBook Air (M3) for credit toward a new Mac.'),
        TradeInValue(device='MacBook Air M2', condition='good', value=430.00,
                     notes='Trade in your MacBook Air (M2) for credit toward a new Mac.'),
        TradeInValue(device='MacBook Air M1', condition='good', value=300.00,
                     notes='Trade in your MacBook Air (M1) for credit toward a new Mac.'),
        TradeInValue(device='iMac', condition='good', value=400.00,
                     notes='Trade in your iMac for credit toward a new Mac.'),
        TradeInValue(device='Mac mini', condition='good', value=240.00,
                     notes='Trade in your Mac mini for credit toward a new Mac.'),
        TradeInValue(device='Mac Studio', condition='good', value=900.00,
                     notes='Trade in your Mac Studio for credit toward a new Mac.'),
        TradeInValue(device='Mac Pro', condition='good', value=1800.00,
                     notes='Trade in your Mac Pro for credit toward a new Mac.'),
        # iPad variants
        TradeInValue(device='iPad Pro 12.9-inch', condition='good', value=480.00,
                     notes='Trade in your iPad Pro 12.9-inch for credit toward a new iPad.'),
        TradeInValue(device='iPad Pro 11-inch', condition='good', value=380.00,
                     notes='Trade in your iPad Pro 11-inch for credit toward a new iPad.'),
        TradeInValue(device='iPad Air', condition='good', value=230.00,
                     notes='Trade in your iPad Air for credit toward a new iPad.'),
        TradeInValue(device='iPad', condition='good', value=130.00,
                     notes='Trade in your iPad for credit toward a new iPad.'),
        TradeInValue(device='iPad mini', condition='good', value=160.00,
                     notes='Trade in your iPad mini for credit toward a new iPad.'),
        # Apple Watch variants
        TradeInValue(device='Apple Watch Ultra 2', condition='good', value=300.00,
                     notes='Trade in your Apple Watch Ultra 2 for credit toward a new Watch.'),
        TradeInValue(device='Apple Watch Ultra', condition='good', value=240.00,
                     notes='Trade in your Apple Watch Ultra for credit toward a new Watch.'),
        TradeInValue(device='Apple Watch Series 10', condition='good', value=180.00,
                     notes='Trade in your Apple Watch Series 10 for credit toward a new Watch.'),
        TradeInValue(device='Apple Watch Series 9', condition='good', value=160.00,
                     notes='Trade in your Apple Watch Series 9 for credit toward a new Watch.'),
        TradeInValue(device='Apple Watch SE (2nd generation)', condition='good', value=80.00,
                     notes='Trade in your Apple Watch SE for credit toward a new Watch.'),
        # AirPods / Vision Pro
        TradeInValue(device='AirPods Pro (2nd generation)', condition='good', value=60.00,
                     notes='Trade in your AirPods Pro (2nd generation) for credit.'),
        TradeInValue(device='AirPods Max', condition='good', value=130.00,
                     notes='Trade in your AirPods Max for credit.'),
        TradeInValue(device='Apple Vision Pro', condition='good', value=1500.00,
                     notes='Trade in your Apple Vision Pro for credit toward a new Apple Vision Pro.'),
    ]
    for tv in trade_in_values:
        db.session.add(tv)
    db.session.commit()
    print(f"Seeded {len(trade_in_values)} trade-in values")

    # --- Support Articles ---
    support_articles = [
        SupportArticle(
            slug='ios-17-new-features', topic='ios',
            title='New features in iOS 17',
            summary='Explore StandBy, NameDrop, and other new features in iOS 17 for iPhone.',
            body='iOS 17 introduces exciting new features including StandBy mode, NameDrop for sharing contact information, Live Voicemail, Journal app, and improvements to Messages, FaceTime, and autocorrect. Compatible with iPhone 12 and later, iPhone SE (3rd generation). iOS 17 brings a more personal, intuitive experience to your iPhone.',
            compat=json.dumps(['iPhone 12', 'iPhone 12 mini', 'iPhone 12 Pro', 'iPhone 12 Pro Max', 'iPhone 13', 'iPhone 13 mini', 'iPhone 13 Pro', 'iPhone 13 Pro Max', 'iPhone 14', 'iPhone 14 Plus', 'iPhone 14 Pro', 'iPhone 14 Pro Max', 'iPhone 15', 'iPhone 15 Plus', 'iPhone 15 Pro', 'iPhone 15 Pro Max', 'iPhone SE (3rd generation)']),
            tags=json.dumps(['ios-17', 'standby', 'namedrop', 'new-features']),
        ),
        SupportArticle(
            slug='apple-repair-options', topic='repair',
            title='Apple Repair Options',
            summary='Learn about the different ways to get Apple Repair service for your device.',
            body='Apple offers several repair options: Mail-in repair — ship your device to an Apple Repair Center. Carry-in repair — bring your device to an Apple Store or Apple Authorized Service Provider. Onsite repair (business only) — certain business customers qualify for onsite repair. Express Replacement Service — receive a replacement before sending the original. Self Service Repair — order parts and tools to repair eligible products yourself.',
            tags=json.dumps(['repair', 'mail-in', 'carry-in', 'apple-repair']),
        ),
        SupportArticle(
            slug='iphone-trade-in-offers', topic='iphone',
            title='iPhone Trade-In Offers',
            summary='Get credit toward a new iPhone when you trade in your eligible device with Apple Trade In.',
            body='Apple Trade In makes it easy to get credit toward a new iPhone. Estimated trade-in values: iPhone 15 Pro Max up to $650, iPhone 14 Pro Max up to $500, iPhone 13 Pro Max up to $440, iPhone 12 Pro Max up to $300, iPhone 11 Pro Max up to $230. Values may vary based on condition. Visit apple.com/trade-in for current trade-in values.',
            tags=json.dumps(['trade-in', 'iphone', 'credit', 'upgrade']),
        ),
        SupportArticle(
            slug='forgot-apple-id-password', topic='apple-id',
            title='If you forgot your Apple ID password',
            summary='Learn how to reset your Apple ID password so you can get back into your account.',
            body='If you forgot your Apple ID password, you can reset it at iforgot.apple.com. You can also reset your password from any trusted Apple device: On iPhone or iPad, go to Settings > [Your Name] > Password & Security > Change Password. On Mac, go to Apple menu > System Settings > [Your Name] > Password & Security > Change Password. If you no longer have access to any of your trusted devices, visit iforgot.apple.com and follow the account recovery process.',
            tags=json.dumps(['apple-id', 'forgot', 'password', 'reset', 'iforgot.apple.com']),
        ),
        SupportArticle(
            slug='apple-watch-series-7-8-9-updates', topic='watch',
            title='Updates in Apple Watch Series 7, 8, and 9',
            summary='Compare the features and updates across Apple Watch Series 7, Series 8, and Series 9.',
            body='Apple Watch has evolved significantly across recent generations. Series 7 (2021): Larger, more crack-resistant display with fast charging, compatible with watchOS 8+. Series 8 (2022): Temperature sensing, Crash Detection, improved workout metrics, compatible with watchOS 9+. Series 9 (2023): S9 SiP chip, Double Tap gesture, brighter 2000-nit display, on-device Siri, precise Find My for iPhone, compatible with watchOS 10+. All three generations support ECG, blood oxygen sensing, and fall detection.',
            tags=json.dumps(['apple-watch', 'series-7', 'series-8', 'series-9', 'watchOS', 'updates']),
        ),
        # --- Additional support articles (expansion to 30+) ---
        SupportArticle(slug='set-up-new-iphone', topic='iphone',
            title='Set up your new iPhone',
            summary='Power on, sign in with Apple ID, and transfer data from your old iPhone or Android.',
            body='To set up your new iPhone: 1) Press and hold the side button to power on. 2) Follow the on-screen Quick Start instructions to use a nearby iPhone or iPad to transfer Apple ID settings. 3) Choose a language and region. 4) Connect to Wi-Fi. 5) Sign in with your Apple ID. 6) Use Quick Start, iCloud Backup, or Move to iOS (for Android) to transfer your data. 7) Set up Face ID or Touch ID. 8) Choose your Siri, Screen Time, and Apple Pay preferences. The setup typically takes 10-20 minutes.',
            compat=json.dumps(['iPhone 15', 'iPhone 15 Plus', 'iPhone 15 Pro', 'iPhone 15 Pro Max', 'iPhone 16', 'iPhone 16 Plus', 'iPhone 16 Pro', 'iPhone 16 Pro Max', 'iPhone 17', 'iPhone 17 Pro', 'iPhone 17 Pro Max']),
            tags=json.dumps(['iphone', 'setup', 'new-device', 'quick-start'])),
        SupportArticle(slug='backup-iphone-icloud', topic='iphone',
            title='Back up your iPhone with iCloud',
            summary='Automatically back up your iPhone to iCloud over Wi-Fi.',
            body='To back up your iPhone with iCloud: go to Settings > [Your Name] > iCloud > iCloud Backup, then toggle "Back Up This iPhone" on. Your iPhone backs up daily when it is connected to power, locked, and on Wi-Fi. You can also tap "Back Up Now" to start a manual backup. iCloud Backup includes app data, device settings, Home screen layout, iMessage / SMS / MMS, photos, videos (if iCloud Photos is off), purchase history, ringtones, and Visual Voicemail password.',
            tags=json.dumps(['iphone', 'backup', 'icloud', 'restore'])),
        SupportArticle(slug='transfer-data-android-to-iphone', topic='iphone',
            title='Move from Android to iPhone',
            summary='Use the Move to iOS app to wirelessly transfer your content from Android to iPhone.',
            body='Move to iOS is a free Apple app that transfers contacts, message history, camera photos and videos, web bookmarks, mail accounts, and calendars from Android to iPhone. Download Move to iOS from Google Play, then when setting up your new iPhone, tap "Move Data from Android" on the Apps & Data screen. Open Move to iOS on your Android, accept terms, enter the code shown on iPhone, and select content to transfer.',
            tags=json.dumps(['iphone', 'android', 'migration', 'move-to-ios'])),
        SupportArticle(slug='find-my-iphone', topic='iphone',
            title='Use Find My to locate your iPhone',
            summary='Locate, lock, or erase your iPhone if you lose it.',
            body='Open the Find My app on another Apple device or sign in to iCloud.com/find. Select your iPhone from the device list. You can play a sound, mark it as lost (this locks the device and displays a custom message), or erase it remotely. Find My works even when your iPhone is offline or powered off (for iPhone 11 and later). Make sure Find My iPhone is enabled in Settings > [Your Name] > Find My > Find My iPhone.',
            tags=json.dumps(['iphone', 'find-my', 'lost', 'security'])),
        SupportArticle(slug='battery-replacement', topic='repair',
            title='iPhone Battery Service',
            summary='Replace your iPhone battery for a flat fee at Apple or an Apple Authorized Service Provider.',
            body='If your iPhone battery has degraded below 80% maximum capacity, consider battery service. Out-of-warranty battery service costs vary by model: iPhone 17, 16, 15 Pro/Pro Max: $99. iPhone 17, 16, 15 / Plus: $99. iPhone 14 and earlier: $89. iPhone SE: $69. AppleCare+ subscribers get battery service at no charge if capacity is below 80%. Service typically takes 3-5 business days for mail-in, or same-day at most Apple Store locations.',
            tags=json.dumps(['battery', 'repair', 'iphone', 'service-cost'])),
        SupportArticle(slug='applecare-plus-overview', topic='applecare',
            title='What is AppleCare+?',
            summary='AppleCare+ extends your warranty and adds accidental damage coverage.',
            body='AppleCare+ extends Apple\'s standard one-year limited warranty and 90 days of complimentary technical support. AppleCare+ adds: unlimited incidents of accidental damage protection (with service fees per incident), 24/7 priority access to Apple experts, express replacement service for iPhone and iPad, and battery service when capacity is below 80%. AppleCare+ with Theft and Loss (iPhone only) also covers up to two incidents of theft or loss per 12-month period.',
            tags=json.dumps(['applecare', 'warranty', 'protection', 'support'])),
        SupportArticle(slug='trade-in-mail-in', topic='trade-in',
            title='How Apple Trade In mail-in works',
            summary='Mail your eligible device to Apple and get instant credit toward a new purchase.',
            body='Apple Trade In mail-in process: 1) Visit apple.com/trade-in and answer questions about your device. 2) Get an estimated trade-in value. 3) Choose to use credit toward a new Apple product or receive an Apple Gift Card. 4) Receive a prepaid shipping label by email. 5) Pack your device (data wipe is automatic; we recommend backing up first). 6) Drop off the package at any UPS location. 7) Apple inspects within 2-3 weeks. 8) Final value is confirmed (it can differ from estimate based on condition). Devices found ineligible are returned at no cost.',
            tags=json.dumps(['trade-in', 'mail-in', 'recycling', 'gift-card'])),
        SupportArticle(slug='order-status-tracking', topic='orders',
            title='Track your Apple Order',
            summary='View order status, shipping updates, and delivery estimates.',
            body='To view your Apple order status, sign in at apple.com/shop/orders or open the Apple Store app. You will see all orders from the last 18 months. Each order shows current status (Processing, Preparing for Shipment, Shipped, Delivered, or Cancelled), estimated delivery date, items, tracking number, and shipping address. Order status updates can take up to 24 hours to reflect new activity. You can also cancel processing orders or initiate returns within 14 days of delivery directly from the order page.',
            tags=json.dumps(['order', 'tracking', 'shipping', 'status'])),
        SupportArticle(slug='return-refund-policy', topic='orders',
            title='Apple Return and Refund Policy',
            summary='Standard Return Policy: 14 days from delivery for most items.',
            body='Apple\'s Standard Return Policy: You can return most items purchased from Apple within 14 days of delivery for a full refund. iPhones must be returned within 14 days and the wireless service plan must be cancelled. Personalized items (engraving, custom-built Mac), opened software, AppleCare plans (more than 30 days), and used or partially used Apple Gift Cards are non-returnable. Returns are free; print a prepaid label from your order page. Refunds appear on your original payment method within 5-10 business days after Apple receives the item.',
            tags=json.dumps(['return', 'refund', 'policy', 'orders'])),
        SupportArticle(slug='cancel-order', topic='orders',
            title='Cancel an order',
            summary='Cancel an order that has not yet shipped from the Order Status page.',
            body='You can cancel an Apple order if it is still in Processing status. To cancel: sign in to apple.com/shop/orders, select the order, then click "Cancel Items". Items already in Preparing for Shipment, Shipped, or Delivered status cannot be cancelled — instead, refuse the delivery or return the item within 14 days. Pre-orders for upcoming products can be modified or cancelled until they enter Preparing for Shipment, typically the day before launch.',
            tags=json.dumps(['order', 'cancel', 'refund'])),
        SupportArticle(slug='apple-pay-setup', topic='apple-pay',
            title='Set up Apple Pay',
            summary='Add credit, debit, or prepaid cards to Apple Pay in the Wallet app.',
            body='To set up Apple Pay on iPhone: Open the Wallet app and tap the + button. Tap "Debit or Credit Card" and follow the prompts. You can scan your card with the camera or enter card information manually. Your bank will verify and may require a one-time verification code via SMS, email, or bank app. Once verified, the card is ready to use. To set a default card, go to Settings > Wallet & Apple Pay > Default Card. Apple Pay works at contactless payment terminals, in apps, and on the web.',
            tags=json.dumps(['apple-pay', 'wallet', 'payment', 'setup'])),
        SupportArticle(slug='macos-update-guide', topic='mac',
            title='Update macOS on your Mac',
            summary='Install the latest macOS update from System Settings.',
            body='To update macOS: Apple menu > System Settings > General > Software Update. If an update is available, click "Update Now" or "Upgrade Now". Keep your Mac plugged in during the update. The update may take 30-60 minutes and your Mac will restart several times. To enable automatic updates: General > Software Update > toggle Automatic Updates. macOS 15 Sequoia is compatible with iMac 2019 and later, MacBook Air 2020 and later, MacBook Pro 2018 and later, Mac mini 2018 and later, Mac Studio 2022 and later, Mac Pro 2019 and later, iMac Pro 2017.',
            compat=json.dumps(['MacBook Air', 'MacBook Pro', 'iMac', 'Mac mini', 'Mac Studio', 'Mac Pro']),
            tags=json.dumps(['mac', 'macos', 'update', 'sequoia'])),
        SupportArticle(slug='ipad-keyboard-pairing', topic='ipad',
            title='Pair Magic Keyboard with iPad',
            summary='Snap on the Magic Keyboard or pair via Bluetooth.',
            body='Magic Keyboard for iPad Pro / iPad Air attaches magnetically and pairs automatically when connected. For Bluetooth pairing: Settings > Bluetooth > turn on Bluetooth, then place your Magic Keyboard near the iPad in pairing mode (hold the power button for 3 seconds). Select the keyboard in the Bluetooth devices list. To adjust keyboard settings (brightness, function keys, modifier keys): Settings > General > Keyboard > Hardware Keyboard.',
            compat=json.dumps(['iPad Pro 11-inch M4', 'iPad Pro 13-inch M4', 'iPad Air 11-inch M4', 'iPad Air 13-inch M4']),
            tags=json.dumps(['ipad', 'keyboard', 'magic-keyboard', 'bluetooth'])),
        SupportArticle(slug='airpods-pairing-pro', topic='airpods',
            title='Pair AirPods Pro with your iPhone',
            summary='Open the case near your iPhone and tap Connect.',
            body='To pair AirPods Pro: Place both AirPods in the charging case. Open the case lid and hold it next to your unlocked iPhone. A setup animation appears on iPhone. Tap "Connect". If prompted, set up Siri and configure Active Noise Cancellation. Your AirPods are now paired with all devices signed into your iCloud account. To check battery level, swipe down from the top-right corner on iPhone to open Control Center, or ask Siri. To take an Ear Tip Fit Test: Settings > AirPods > Ear Tip Fit Test.',
            compat=json.dumps(['iPhone 15', 'iPhone 16', 'iPhone 17', 'iPad Air M4', 'iPad Pro M5']),
            tags=json.dumps(['airpods', 'pro', 'pairing', 'bluetooth', 'setup'])),
        SupportArticle(slug='reset-airpods', topic='airpods',
            title='Reset your AirPods',
            summary='Resolve connection issues by resetting AirPods to factory.',
            body='To reset AirPods: 1) Put both AirPods in the case and close the lid. 2) Wait 30 seconds. 3) Open the lid. 4) On iPhone, go to Settings > Bluetooth, tap the info button next to your AirPods, tap "Forget This Device", then confirm. 5) With the case lid open, press and hold the setup button on the back of the case for about 15 seconds, until the status light flashes amber, then white. 6) Reconnect by placing AirPods near iPhone with the case open and tap Connect.',
            tags=json.dumps(['airpods', 'reset', 'troubleshoot'])),
        SupportArticle(slug='apple-vision-pro-setup', topic='vision',
            title='Set up Apple Vision Pro',
            summary='Optic ID, Light Seal sizing, and downloading apps for visionOS.',
            body='Setting up Apple Vision Pro: 1) Hold the top button to power on. 2) Pair with your iPhone for a quick setup (alternatively use the on-device setup). 3) Configure Optic ID — your iris-based authentication. 4) Calibrate eye and hand tracking. 5) Choose your Light Seal size for best fit. 6) Sign in with Apple ID. 7) Set up Persona for FaceTime. 8) Apps are downloaded from the visionOS App Store. Vision Pro currently weighs approximately 600 grams and uses a 2-hour external battery.',
            tags=json.dumps(['vision-pro', 'visionos', 'setup', 'optic-id'])),
        SupportArticle(slug='apple-id-two-factor', topic='apple-id',
            title='Turn on two-factor authentication for your Apple ID',
            summary='Add an extra layer of security with trusted devices and phone numbers.',
            body='To turn on two-factor authentication for your Apple ID: On iPhone or iPad, Settings > [Your Name] > Sign-In & Security > Two-Factor Authentication, then tap Turn On. On Mac, Apple menu > System Settings > [Your Name] > Sign-In & Security. Enter a phone number that can receive verification codes via SMS or phone call. Trust your current device. After enabling, signing in to a new device or browser requires both your password and a 6-digit verification code sent to a trusted device. Two-factor authentication cannot be turned off once enabled for an Apple ID created in iOS 13.4 or later.',
            tags=json.dumps(['apple-id', 'two-factor', 'security', '2fa'])),
        SupportArticle(slug='family-sharing-setup', topic='apple-id',
            title='Set up Family Sharing',
            summary='Share App Store, Apple Music, iCloud+, and more with up to five family members.',
            body='Family Sharing lets up to six people share App Store purchases, Apple Music Family, Apple TV+, Apple Arcade, iCloud+ storage, an Apple One subscription, family calendars, and photos. To set up: Settings > [Your Name] > Family Sharing > Set Up Your Family. Add members by sending an iMessage invitation or creating child accounts. You can require Ask to Buy for child accounts, share locations, and use Screen Time across all family devices. Some content (subscriptions, in-app purchases, books) is not shareable.',
            tags=json.dumps(['family-sharing', 'apple-id', 'subscription', 'parental-controls'])),
        SupportArticle(slug='icloud-storage-plans', topic='icloud',
            title='iCloud+ storage plans and pricing',
            summary='Upgrade beyond the free 5GB tier for more storage and Private Relay.',
            body='iCloud+ plans include extra storage plus Private Relay, Hide My Email, custom email domain, and HomeKit Secure Video. United States pricing (monthly): Free 5GB, 50GB $0.99, 200GB $2.99, 2TB $9.99, 6TB $29.99, 12TB $59.99. Plans 200GB and above can be shared with Family Sharing members. To upgrade: Settings > [Your Name] > iCloud > Manage Account Storage > Change Storage Plan.',
            tags=json.dumps(['icloud', 'storage', 'pricing', 'icloud-plus'])),
        SupportArticle(slug='apple-music-subscribe', topic='apple-music',
            title='Subscribe to Apple Music',
            summary='Plans for individuals, students, families, and Apple One bundles.',
            body='Apple Music plans (US): Voice $4.99/month, Student $5.99/month (with student verification through UNiDAYS, eligible 4 years), Individual $10.99/month, Family $16.99/month (up to 6 people). Apple One bundles Apple Music with iCloud+, Arcade, and TV+ starting at $19.95/month (Individual). Subscribe in the Apple Music app, in Settings > [Your Name] > Subscriptions, or at music.apple.com. First-time subscribers can get a one-month free trial.',
            tags=json.dumps(['apple-music', 'subscription', 'plans', 'pricing'])),
        SupportArticle(slug='ios-18-features', topic='ios',
            title='What\'s new in iOS 18',
            summary='Customizable Home Screen, redesigned Photos, Apple Intelligence, and more.',
            body='iOS 18 brings major updates including: Customizable Home Screen with dark/tinted icons, redesigned Photos app, deeply customizable Control Center, RCS messaging support, scheduled message sending, satellite Messages, redesigned Mail with categorization, Passwords app, and Apple Intelligence (compatible with iPhone 15 Pro, 15 Pro Max, and all iPhone 16/17 models). iOS 18 is compatible with iPhone XS and later.',
            compat=json.dumps(['iPhone XS', 'iPhone 11', 'iPhone 12', 'iPhone 13', 'iPhone 14', 'iPhone 15', 'iPhone 16', 'iPhone 17', 'iPhone SE (2nd generation)', 'iPhone SE (3rd generation)']),
            tags=json.dumps(['ios-18', 'apple-intelligence', 'home-screen', 'new-features'])),
        SupportArticle(slug='macos-sequoia-features', topic='mac',
            title='What\'s new in macOS Sequoia',
            summary='iPhone Mirroring, window tiling, Passwords app, and Apple Intelligence on Mac.',
            body='macOS Sequoia (macOS 15) introduces iPhone Mirroring (control your iPhone from your Mac), enhanced window tiling with drag-to-corner snapping, the new Passwords app, redesigned Safari with Highlights, Apple Intelligence on Apple silicon Macs, and major updates to Notes, Messages, and Maps. Compatible with Mac models from 2018 and later (Intel) and all Apple silicon Macs.',
            tags=json.dumps(['macos', 'sequoia', 'iphone-mirroring', 'apple-intelligence'])),
        SupportArticle(slug='watchos-11-features', topic='watch',
            title='What\'s new in watchOS 11',
            summary='Vitals app, training load, customizable Activity rings, and Smart Stack.',
            body='watchOS 11 introduces: Vitals app to track overnight health metrics; Training Load to evaluate workout intensity; pausable Activity rings; smarter Smart Stack with live activities; redesigned Photos face; Translate app; new Check In feature for Messages. Compatible with Apple Watch Series 6 and later, including Apple Watch Ultra (1 and 2) and Apple Watch SE (2nd gen).',
            compat=json.dumps(['Apple Watch Series 6', 'Apple Watch Series 7', 'Apple Watch Series 8', 'Apple Watch Series 9', 'Apple Watch Series 10', 'Apple Watch Series 11', 'Apple Watch SE (2nd generation)', 'Apple Watch Ultra', 'Apple Watch Ultra 2', 'Apple Watch Ultra 3']),
            tags=json.dumps(['watchos-11', 'vitals', 'training-load'])),
        SupportArticle(slug='clean-iphone-water', topic='iphone',
            title='Clean liquid from your iPhone Lightning or USB-C port',
            summary='If your iPhone says "Liquid Detected", do not charge until the port is dry.',
            body='If your iPhone displays a "Liquid Detected in Lightning Connector" or "Liquid Detected in USB-C Connector" alert: 1) Unplug the cable. 2) Tap the iPhone gently against your hand with the connector facing down to remove excess liquid. 3) Leave the iPhone in a dry area with airflow for at least 30 minutes. 4) Try charging again. Do NOT dry your iPhone with an external heat source or compressed air, and do not insert a cotton swab or paper towel into the connector. iPhone 12 and later are IP68 rated.',
            tags=json.dumps(['iphone', 'liquid', 'water-damage', 'lightning', 'usb-c'])),
        SupportArticle(slug='accessibility-features', topic='accessibility',
            title='Accessibility features overview',
            summary='Built-in accessibility for Vision, Hearing, Mobility, Speech, and Cognitive.',
            body='Apple devices include comprehensive built-in accessibility: VoiceOver screen reader, Zoom, Display & Text Size, Spoken Content, Audio Descriptions (Vision); Made for iPhone hearing aids, Live Captions, Sound Recognition (Hearing); AssistiveTouch, Voice Control, Switch Control (Mobility); Personal Voice, Live Speech (Speech); Guided Access, Background Sounds, Spoken Content (Cognitive). Enable in Settings > Accessibility on iPhone/iPad/Mac, or via the triple-click side button shortcut.',
            tags=json.dumps(['accessibility', 'voiceover', 'live-captions', 'switch-control'])),
        SupportArticle(slug='self-service-repair', topic='repair',
            title='Apple Self Service Repair',
            summary='Order genuine Apple parts, tools, and manuals to repair eligible products yourself.',
            body='Apple Self Service Repair gives individual customers access to the same parts, tools, and repair manuals used at Apple Stores. The program currently covers iPhone (12 series and later), select MacBook Pro and MacBook Air models with Apple silicon, Studio Display, and iMac. Visit selfservicerepair.com to order parts. You can rent a tool kit for one week ($49) or buy individual tools. After repair, return original parts for recycling and potential credit. Self Service Repair is recommended for experienced technicians.',
            tags=json.dumps(['self-service-repair', 'parts', 'tools', 'diy'])),
        SupportArticle(slug='find-serial-number', topic='general',
            title='Find the serial number of your Apple product',
            summary='Locate the serial number for warranty and repair lookups.',
            body='To find the serial number: On iPhone, iPad, iPod touch — Settings > General > About > Serial Number. On Mac — Apple menu > About This Mac. On Apple Watch — Settings > General > About on the Watch, or in the Apple Watch app on iPhone. On AirPods — open the case lid near your iPhone, go to Settings > Bluetooth > info icon next to your AirPods. You can also find the serial number on the original packaging or printed on the device itself (for older Macs and iPhones).',
            tags=json.dumps(['serial-number', 'warranty', 'lookup', 'general'])),
        SupportArticle(slug='vision-pro-prescription-lenses', topic='vision',
            title='ZEISS Optical Inserts for Apple Vision Pro',
            summary='Order custom prescription lenses for Apple Vision Pro.',
            body='If you wear glasses, you need ZEISS Optical Inserts to use Apple Vision Pro. Order them during Vision Pro purchase or separately at apple.com. Inserts cost $99 for readers (single vision +0.25 to +3.50) or $149 for prescription (sphere -10.00 to +6.00, cylinder up to ±5.00). Upload a current prescription (issued within the last 24 months). Inserts attach magnetically to the Vision Pro and are encoded automatically so the device knows your prescription is in place.',
            tags=json.dumps(['vision-pro', 'zeiss', 'prescription', 'lenses'])),
        SupportArticle(slug='homepod-airplay-setup', topic='homepod',
            title='Set up AirPlay 2 with HomePod',
            summary='Stream audio from iPhone, iPad, Mac, or Apple TV to one or more HomePods.',
            body='HomePod automatically uses AirPlay 2 for multi-room audio. To play to a HomePod: from Control Center on iPhone/iPad, tap the AirPlay icon in the audio card and select one or more HomePods. In the Home app, tap the HomePod, then Settings > Stereo Pair to pair two HomePods. AirPlay 2 supports lossless audio with HomePod (2nd gen) and HomePod mini. For Mac, click the AirPlay icon in the menu bar; Apple TV uses Settings > AirPlay and HomeKit.',
            compat=json.dumps(['HomePod', 'HomePod mini', 'HomePod (2nd generation)']),
            tags=json.dumps(['homepod', 'airplay', 'multi-room', 'audio'])),
        SupportArticle(slug='apple-store-pickup', topic='orders',
            title='In-store pickup at Apple Store',
            summary='Reserve eligible items online and pick them up at a nearby Apple Store.',
            body='To use Apple Store pickup: select an item in the Apple Store online or in-app, choose "Pick Up" instead of delivery, enter your ZIP code to see nearby stores with availability, choose a store and pickup window. You\'ll receive an email confirmation with a pickup code. Bring photo ID and the email to the store. Most pickups are available within an hour; some configurations may take longer. Pickup is available for most in-stock iPhones, iPads, Apple Watches, AirPods, accessories, and Mac configurations.',
            tags=json.dumps(['store-pickup', 'reservation', 'order', 'apple-store'])),
    ]
    for sa in support_articles:
        db.session.add(sa)
    db.session.commit()
    print(f"Seeded {len(support_articles)} support articles")


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

def _get_product(name_fragment):
    """Return first product whose name contains name_fragment (case-insensitive)."""
    return Product.query.filter(Product.name.ilike(f'%{name_fragment}%')).first()


def seed_benchmark_users():
    """Seed 4 benchmark users with addresses, payment methods, orders, and cart items.
    Called AFTER expand_catalog.py. Idempotent — checks if users exist first.
    """
    if User.query.filter_by(email='alice.j@test.com').first():
        return

    from datetime import timedelta

    # ------------------------------------------------------------------
    # Create users
    # ------------------------------------------------------------------
    users_data = [
        dict(first_name='Alice', last_name='Johnson', email='alice.j@test.com',
             phone='415-555-0101', city='San Francisco', state='CA', zip_code='94103',
             address='742 Market Street'),
        dict(first_name='Bob', last_name='Chen', email='bob.c@test.com',
             phone='650-555-0102', city='Palo Alto', state='CA', zip_code='94301',
             address='350 University Avenue'),
        dict(first_name='Carol', last_name='Davis', email='carol.d@test.com',
             phone='310-555-0103', city='Los Angeles', state='CA', zip_code='90028',
             address='6801 Hollywood Boulevard'),
        dict(first_name='David', last_name='Kim', email='david.k@test.com',
             phone='212-555-0104', city='New York', state='NY', zip_code='10001',
             address='500 8th Avenue'),
    ]

    users = []
    for ud in users_data:
        u = User(
            first_name=ud['first_name'], last_name=ud['last_name'],
            email=ud['email'], phone=ud['phone'],
            address=ud['address'], city=ud['city'],
            state=ud['state'], zip_code=ud['zip_code'],
        )
        u.password_hash = PINNED_PASSWORD_HASH
        db.session.add(u)
        users.append(u)
    db.session.flush()  # get IDs

    alice, bob, carol, david = users

    # ------------------------------------------------------------------
    # Saved Addresses
    # ------------------------------------------------------------------
    def mk_addr(user, label, fn, ln, addr, city, state, zip_, phone, default=False):
        a = SavedAddress(user_id=user.id, label=label, first_name=fn, last_name=ln,
                         address=addr, city=city, state=state, zip_code=zip_,
                         phone=phone, is_default=default)
        db.session.add(a)
        return a

    # Alice — home + work
    mk_addr(alice, 'Home', 'Alice', 'Johnson', '742 Market Street', 'San Francisco', 'CA', '94103', '415-555-0101', default=True)
    mk_addr(alice, 'Work', 'Alice', 'Johnson', '1 Infinite Loop', 'Cupertino', 'CA', '95014', '415-555-0101')
    mk_addr(alice, 'Gift', 'Mom', 'Johnson', '88 Pine Street', 'Seattle', 'WA', '98101', '206-555-0201')

    # Bob — home + work
    mk_addr(bob, 'Home', 'Bob', 'Chen', '350 University Avenue', 'Palo Alto', 'CA', '94301', '650-555-0102', default=True)
    mk_addr(bob, 'Work', 'Bob', 'Chen', '2550 Garcia Ave', 'Mountain View', 'CA', '94043', '650-555-0102')

    # Carol — home + gift
    mk_addr(carol, 'Home', 'Carol', 'Davis', '6801 Hollywood Boulevard', 'Los Angeles', 'CA', '90028', '310-555-0103', default=True)
    mk_addr(carol, 'Gift', 'Sarah', 'Davis', '4320 Sunset Drive', 'Austin', 'TX', '78701', '512-555-0301')
    mk_addr(carol, 'Work', 'Carol', 'Davis', '2121 Avenue of the Stars', 'Los Angeles', 'CA', '90067', '310-555-0103')

    # David — home + work + gift
    mk_addr(david, 'Home', 'David', 'Kim', '500 8th Avenue', 'New York', 'NY', '10001', '212-555-0104', default=True)
    mk_addr(david, 'Work', 'David', 'Kim', '11 Penn Plaza', 'New York', 'NY', '10001', '212-555-0104')
    mk_addr(david, 'Gift', 'Mom', 'Kim', '42 Elm Street', 'Flushing', 'NY', '11354', '718-555-0309')

    # ------------------------------------------------------------------
    # Payment Methods
    # ------------------------------------------------------------------
    def mk_pm(user, card_type, last4, exp_m, exp_y, name, default=False):
        if default:
            PaymentMethod.query.filter_by(user_id=user.id, is_default=True).update({'is_default': False})
        pm = PaymentMethod(user_id=user.id, card_type=card_type, last4=last4,
                           exp_month=exp_m, exp_year=exp_y, cardholder_name=name,
                           is_default=default)
        db.session.add(pm)
        return pm

    mk_pm(alice, 'Visa',       '4242', 12, 2027, 'Alice Johnson', default=True)
    mk_pm(alice, 'Mastercard', '5555', 3,  2026, 'Alice Johnson')
    mk_pm(alice, 'Visa',       '1234', 9,  2028, 'Alice M Johnson')

    mk_pm(bob, 'Visa',       '6789', 6, 2026, 'Bob Chen', default=True)
    mk_pm(bob, 'Amex',       '0001', 11, 2027, 'Bob Chen')

    mk_pm(carol, 'Mastercard', '3344', 8, 2027, 'Carol Davis', default=True)
    mk_pm(carol, 'Visa',       '7788', 1, 2029, 'Carol Davis')
    mk_pm(carol, 'Amex',       '9900', 5, 2026, 'Carol Davis')

    mk_pm(david, 'Visa',       '2468', 4, 2028, 'David Kim', default=True)
    mk_pm(david, 'Mastercard', '1357', 7, 2027, 'David Kim')

    db.session.flush()

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------
    _order_seq = {'n': 0}
    def mk_order(user, status, product_name, qty, color, storage, days_ago,
                 ship_addr=None, pay='Visa ending in 4242'):
        p = _get_product(product_name)
        if not p:
            return None
        total = p.price * qty
        if ship_addr:
            addr_str = f"{ship_addr.address}, {ship_addr.city}, {ship_addr.state} {ship_addr.zip_code}"
        else:
            addr_str = f"{user.address}, {user.city}, {user.state} {user.zip_code}"
        _order_seq['n'] += 1
        order = Order(
            user_id=user.id,
            order_number=f"APL-{_order_seq['n']:05X}",
            status=status,
            total=total,
            shipping_address=addr_str,
            shipping_method='standard',
            payment_method=pay,
            created_at=MIRROR_REFERENCE_DATE - timedelta(days=days_ago),
            updated_at=MIRROR_REFERENCE_DATE - timedelta(days=days_ago),
        )
        db.session.add(order)
        db.session.flush()
        oi = OrderItem(order_id=order.id, product_id=p.id, quantity=qty,
                       price=p.price, color=color, storage=storage)
        db.session.add(oi)
        return order

    alice_addrs = SavedAddress.query.filter_by(user_id=alice.id).all()
    alice_home = next((a for a in alice_addrs if a.label == 'Home'), alice_addrs[0])
    alice_work = next((a for a in alice_addrs if a.label == 'Work'), alice_addrs[0])

    mk_order(alice, 'delivered',  'iPhone 17 Pro', 1, 'Black Titanium', '256GB', 45,
             ship_addr=alice_home, pay='Visa ending in 4242')
    mk_order(alice, 'shipped',    'AirPods Pro',   1, '',               '',      8,
             ship_addr=alice_home, pay='Mastercard ending in 5555')
    mk_order(alice, 'processing', 'MacBook Air 13', 1, 'Midnight',      '256GB', 1,
             ship_addr=alice_work, pay='Visa ending in 4242')
    mk_order(alice, 'cancelled',  'Apple Watch Series 9', 1, 'Midnight', '41mm', 30,
             ship_addr=alice_home, pay='Visa ending in 4242')
    mk_order(alice, 'delivered',  'iPad Pro 11',   1, 'Space Black',    '256GB', 90,
             ship_addr=alice_home, pay='Visa ending in 1234')

    mk_order(bob, 'delivered',  'iPhone 15',        1, 'Blue', '128GB', 60, pay='Visa ending in 6789')
    mk_order(bob, 'processing', 'AirPods 4',        1, '',     '',      2,  pay='Amex ending in 0001')
    mk_order(bob, 'shipped',    'Apple Watch SE',   1, 'Midnight', '40mm', 14, pay='Visa ending in 6789')
    mk_order(bob, 'cancelled',  'HomePod mini',     1, 'Yellow', '',    20,  pay='Visa ending in 6789')

    carol_addrs = SavedAddress.query.filter_by(user_id=carol.id).all()
    carol_gift = next((a for a in carol_addrs if a.label == 'Gift'), carol_addrs[0])
    mk_order(carol, 'delivered',  'iPhone 17',        1, 'Pink',   '128GB', 50,
             ship_addr=carol_gift, pay='Mastercard ending in 3344')
    mk_order(carol, 'shipped',    'AirPods Max',      1, 'Blue',   '',      10,
             pay='Visa ending in 7788')
    mk_order(carol, 'processing', 'iPad Air',         1, 'Blue',   '256GB', 2,
             pay='Mastercard ending in 3344')
    mk_order(carol, 'delivered',  'Apple Pencil Pro', 1, '',       '',      35,
             pay='Amex ending in 9900')

    mk_order(david, 'delivered',  'MacBook Pro 16',   1, 'Space Black', '512GB', 70, pay='Visa ending in 2468')
    mk_order(david, 'delivered',  'iPhone 17 Pro Max', 1, 'Natural Titanium', '512GB', 40, pay='Visa ending in 2468')
    mk_order(david, 'shipped',    'Apple Vision Pro',  1, '',  '',      15, pay='Mastercard ending in 1357')
    mk_order(david, 'processing', 'MacBook Air 15',    1, 'Silver', '512GB', 1, pay='Visa ending in 2468')
    mk_order(david, 'cancelled',  'Mac mini',          1, 'Silver', '',     25, pay='Mastercard ending in 1357')

    # ------------------------------------------------------------------
    # Pre-seed cart for Alice
    # ------------------------------------------------------------------
    for name_frag, color, storage in [
        ('iPhone 17 Pro', 'Desert Titanium', '128GB'),
        ('AirPods Pro',   '',                ''),
    ]:
        p = _get_product(name_frag)
        if p:
            ci = CartItem(user_id=alice.id, product_id=p.id, quantity=1,
                          color=color, storage=storage)
            db.session.add(ci)

    db.session.commit()
    print("Seeded 4 benchmark users (alice, bob, carol, david) with addresses, payments, orders, and cart items.")


# ---------------------------------------------------------------------------
# Extra catalog (legacy iPhones, older Watches, more cases/cables) — pushes
# product count past 150 while staying inside the Apple lineup envelope.
# ---------------------------------------------------------------------------

EXTRA_PRODUCTS = [
    # (name, slug, category, subcategory, subtitle, description, price, monthly_price, months,
    #  colors[], storage[], specs_dict, release_year, chip_family)
    ('iPhone 14', 'iphone-14', 'iphone', '', 'Iconic camera. Brilliant display.',
     'A15 Bionic chip, dual-camera system with 12MP Main and 12MP Ultra Wide, 6.1-inch Super Retina XDR display.',
     699.00, 29.12, ['Midnight', 'Starlight', 'Red', 'Blue', 'Purple', 'Yellow'],
     ['128GB', '256GB', '512GB'],
     {'chip': 'A15 Bionic', 'display': '6.1" Super Retina XDR', 'camera': '12MP Main + 12MP Ultra Wide'},
     2022, 'A15 Bionic'),
    ('iPhone 14 Plus', 'iphone-14-plus', 'iphone', '', 'Big and bigger.',
     'A15 Bionic chip with 5-core GPU, 6.7-inch Super Retina XDR display, two-day battery on the bigger model.',
     799.00, 33.29, ['Midnight', 'Starlight', 'Red', 'Blue', 'Purple', 'Yellow'],
     ['128GB', '256GB', '512GB'],
     {'chip': 'A15 Bionic', 'display': '6.7" Super Retina XDR'}, 2022, 'A15 Bionic'),
    ('iPhone 12 Pro', 'iphone-12-pro', 'iphone', '', 'It is a leap year.',
     'A14 Bionic chip, Pro camera system with LiDAR, Ceramic Shield.',
     699.00, 29.12, ['Pacific Blue', 'Gold', 'Graphite', 'Silver'],
     ['128GB', '256GB', '512GB'],
     {'chip': 'A14 Bionic', 'display': '6.1" Super Retina XDR'}, 2020, 'A14 Bionic'),
    ('iPhone 12 Pro Max', 'iphone-12-pro-max', 'iphone', '', 'It is a leap year.',
     'A14 Bionic, 6.7-inch Super Retina XDR display, Pro camera system with LiDAR Scanner.',
     799.00, 33.29, ['Pacific Blue', 'Gold', 'Graphite', 'Silver'],
     ['128GB', '256GB', '512GB'],
     {'chip': 'A14 Bionic', 'display': '6.7" Super Retina XDR'}, 2020, 'A14 Bionic'),
    ('iPhone 11 Pro', 'iphone-11-pro', 'iphone', '', 'Pro. Beyond.',
     'A13 Bionic chip, triple-camera system, Super Retina XDR display.',
     599.00, 24.95, ['Midnight Green', 'Space Gray', 'Silver', 'Gold'],
     ['64GB', '256GB', '512GB'],
     {'chip': 'A13 Bionic', 'display': '5.8" Super Retina XDR'}, 2019, 'A13 Bionic'),
    ('iPhone 11 Pro Max', 'iphone-11-pro-max', 'iphone', '', 'Pro. Beyond.',
     'A13 Bionic, 6.5-inch Super Retina XDR display, longest battery life in an iPhone.',
     699.00, 29.12, ['Midnight Green', 'Space Gray', 'Silver', 'Gold'],
     ['64GB', '256GB', '512GB'],
     {'chip': 'A13 Bionic', 'display': '6.5" Super Retina XDR'}, 2019, 'A13 Bionic'),
    ('iPhone XR', 'iphone-xr', 'iphone', '', 'Brilliant. In every way.',
     'A12 Bionic chip, 6.1-inch Liquid Retina LCD, advanced single-camera system.',
     349.00, 14.54, ['White', 'Black', 'Blue', 'Yellow', 'Coral', 'Red'],
     ['64GB', '128GB', '256GB'],
     {'chip': 'A12 Bionic', 'display': '6.1" Liquid Retina LCD'}, 2018, 'A12 Bionic'),
    ('iPhone XS', 'iphone-xs', 'iphone', '', 'Welcome to the big screens.',
     'A12 Bionic, dual-camera system, 5.8-inch Super Retina display.',
     449.00, 18.70, ['Space Gray', 'Silver', 'Gold'],
     ['64GB', '256GB', '512GB'],
     {'chip': 'A12 Bionic', 'display': '5.8" Super Retina'}, 2018, 'A12 Bionic'),
    ('iPhone SE (2nd generation)', 'iphone-se-2nd-gen', 'iphone', '', 'Lots to love. Less to spend.',
     'A13 Bionic, 4.7-inch Retina HD display, Touch ID Home button.',
     299.00, 12.45, ['Black', 'White', 'Red'],
     ['64GB', '128GB', '256GB'],
     {'chip': 'A13 Bionic', 'display': '4.7" Retina HD'}, 2020, 'A13 Bionic'),
    ('Apple Watch Series 7', 'apple-watch-series-7', 'watch', '', 'It is our largest display yet.',
     'Larger, more crack-resistant display, fast charging, S7 SiP.',
     249.00, 10.37, ['Midnight', 'Starlight', 'Green', 'Blue', 'Red'],
     ['41mm', '45mm'],
     {'chip': 'S7', 'display': 'Always-On Retina'}, 2021, ''),
    ('Apple Watch Series 6', 'apple-watch-series-6', 'watch', '', 'The future of health is on your wrist.',
     'Blood oxygen sensing, S6 SiP, Always-On Retina display.',
     199.00, 8.29, ['Space Gray', 'Silver', 'Gold', 'Blue', 'Red'],
     ['40mm', '44mm'],
     {'chip': 'S6', 'display': 'Always-On Retina'}, 2020, ''),
    ('Apple Watch SE (1st generation)', 'apple-watch-se-1st-gen', 'watch', '', 'Heavy on features. Light on price.',
     'S5 SiP, Retina display, all-day battery life.',
     179.00, 7.45, ['Space Gray', 'Silver', 'Gold'],
     ['40mm', '44mm'],
     {'chip': 'S5', 'display': 'Retina LTPO OLED'}, 2020, ''),
    ('iPad mini 7', 'ipad-mini-7', 'ipad', 'ipad-mini', 'Mega power. Mini sized.',
     'A17 Pro chip, Apple Pencil Pro support, 8.3-inch Liquid Retina display.',
     499.00, 20.79, ['Space Gray', 'Blue', 'Purple', 'Starlight'],
     ['128GB', '256GB', '512GB'],
     {'chip': 'A17 Pro', 'display': '8.3" Liquid Retina'}, 2024, 'A17 Pro'),
    ('iPad Pro 12.9-inch (6th generation)', 'ipad-pro-129-6th-gen', 'ipad', 'ipad-pro', 'Supercharged by M2.',
     'M2 chip, Liquid Retina XDR display, Apple Pencil hover.',
     1099.00, 45.79, ['Space Gray', 'Silver'],
     ['128GB', '256GB', '512GB', '1TB', '2TB'],
     {'chip': 'M2', 'display': '12.9" Liquid Retina XDR'}, 2022, 'M2'),
    ('MacBook Pro 13-inch (M2)', 'macbook-pro-13-m2', 'mac', 'macbook-pro', 'Power to go.',
     'Apple M2 chip, 13.3-inch Retina display, Touch Bar.',
     1299.00, 54.12, ['Space Gray', 'Silver'],
     ['256GB', '512GB', '1TB', '2TB'],
     {'chip': 'M2', 'display': '13.3" Retina'}, 2022, 'M2'),
    ('Mac mini M1', 'mac-mini-m1', 'mac', 'mac-mini', 'More mini. More mighty.',
     'Apple M1 chip, up to 16GB unified memory.',
     699.00, 29.12, ['Silver'],
     ['256GB', '512GB', '1TB', '2TB'],
     {'chip': 'M1', 'memory': '8GB / 16GB'}, 2020, 'M1'),
    ('iMac 21.5-inch (Intel)', 'imac-215-intel', 'mac', 'imac', 'Performance and design. Taken right to the edge.',
     '21.5-inch Retina 4K display, 8th-generation Intel Core processors.',
     999.00, 41.62, ['Silver'],
     ['256GB', '512GB', '1TB'],
     {'chip': 'Intel Core i5', 'display': '21.5" Retina 4K'}, 2019, ''),
    ('HomePod (1st generation)', 'homepod-1st-gen', 'homepod', '', 'A breakthrough in sound.',
     'Spatial awareness, seven-tweeter array, A8 chip.',
     299.00, 12.45, ['Space Gray', 'White'],
     [],
     {'chip': 'A8', 'audio': '360-degree, room-sensing'}, 2018, ''),
    ('Apple TV HD', 'apple-tv-hd', 'tv', '', 'The future of television.',
     'A8 chip, Siri Remote, 1080p HD output, App Store on tvOS.',
     149.00, 6.20, ['Black'],
     ['32GB'],
     {'chip': 'A8', 'output': '1080p HD'}, 2015, ''),
    ('iPhone 13 Silicone Case with MagSafe', 'iphone-13-silicone-case-magsafe', 'accessories', 'iphone-case',
     'Designed by Apple to complement iPhone 13.',
     'Silicone exterior, soft microfiber lining, MagSafe magnets, snap-on attachment.',
     49.00, None, ['Pink Pomelo', 'Blue Fog', 'Eucalyptus', 'Marigold', 'Midnight'],
     [], {'compat': 'iPhone 13', 'features': 'MagSafe, microfiber lining'}, 2021, ''),
    ('iPhone 15 Clear Case with MagSafe', 'iphone-15-clear-case-magsafe', 'accessories', 'iphone-case',
     'Show off iPhone 15 in its full color.',
     'Crystal-clear polycarbonate, MagSafe magnets, scratch-resistant coating.',
     49.00, None, ['Clear'],
     [], {'compat': 'iPhone 15', 'features': 'MagSafe'}, 2023, ''),
    ('Smart Folio for iPad (10th generation)', 'smart-folio-ipad-10', 'accessories', 'ipad-accessory',
     'Front and back protection.',
     'Polyurethane Smart Folio for iPad (10th generation) with auto wake/sleep.',
     79.00, None, ['White', 'Sky', 'Watermelon', 'Lemonade', 'Charcoal Gray'],
     [], {'compat': 'iPad (10th generation)'}, 2022, ''),
    ('USB-C to MagSafe 3 Cable (2m)', 'usbc-magsafe3-cable-2m', 'accessories', 'cable',
     'Quick-release safety connector for MacBook Pro.',
     '2-metre USB-C to MagSafe 3 cable in woven design. Fast-charging supported.',
     49.00, None, ['Space Black', 'Silver', 'Starlight', 'Midnight'],
     [], {'features': 'MagSafe 3, woven, fast-charging'}, 2021, ''),
    ('Beats Solo Buds', 'beats-solo-buds', 'airpods', '', 'Powerful sound. All-day battery.',
     'Compact wireless earbuds, up to 18 hours of listening time.',
     79.99, None, ['Matte Black', 'Storm Gray', 'Arctic Purple', 'Transparent Red'],
     [], {'audio': 'Custom-tuned', 'battery': 'Up to 18 hours'}, 2024, ''),
    ('Beats Studio3 Wireless', 'beats-studio3-wireless', 'airpods', '', 'Pure adaptive noise cancelling.',
     'Over-ear noise cancelling headphones, Class 1 Bluetooth, up to 22 hours of battery.',
     349.99, None, ['Matte Black', 'Shadow Gray', 'White', 'Red'],
     [], {'chip': 'Apple W1', 'anc': 'Pure ANC'}, 2017, ''),
    ('Magic Mouse', 'magic-mouse-legacy', 'accessories', 'mac-accessory', 'Multi-Touch surface.',
     'Wireless Magic Mouse with Multi-Touch surface and rechargeable battery.',
     99.00, None, ['White'],
     [], {'features': 'Multi-Touch, Lightning charge'}, 2017, ''),
    ('Magic Keyboard with Touch ID', 'magic-keyboard-touchid', 'accessories', 'mac-accessory',
     'Faster sign-in. Compact layout.',
     'Magic Keyboard with Touch ID for Apple silicon Mac. Compact layout.',
     149.00, None, ['White'],
     [], {'features': 'Touch ID, USB-C charge'}, 2021, ''),
    ('AirPods (3rd generation) Lightning Case', 'airpods-3-lightning-case-spare', 'accessories', 'airpods-case',
     'Replacement charging case.',
     'Spare Lightning charging case for AirPods (3rd generation).',
     79.00, None, ['White'],
     [], {'compat': 'AirPods 3rd gen'}, 2021, ''),
    ('Lightning to USB-C Cable (1m)', 'lightning-usbc-cable-1m', 'accessories', 'cable',
     'Sync and fast-charge.',
     '1-metre Lightning to USB-C cable. Supports fast charging on iPhone 8 and later.',
     19.00, None, ['White'],
     [], {'features': 'Fast-charging'}, 2017, ''),
    ('Thunderbolt 4 Pro Cable (1.8m)', 'thunderbolt-4-pro-cable', 'accessories', 'cable',
     'Up to 40 Gb/s data transfer.',
     'Thunderbolt 4 Pro cable supports up to 40 Gb/s and 100W charging.',
     129.00, None, ['Space Black'],
     [], {'features': '40 Gb/s, 100W'}, 2022, ''),
    ('20W USB-C Power Adapter (Refresh)', 'usbc-power-adapter-20w-2024', 'accessories', 'charger',
     'Fast charge for iPhone and iPad.',
     'Compact 20W USB-C charger compatible with iPhone, iPad, and AirPods.',
     19.00, None, ['White'],
     [], {'output': '20W USB-C'}, 2024, ''),
    ('Apple Watch Pride Edition Sport Band', 'apple-watch-pride-band', 'accessories', 'watch-band',
     'Celebrate every voice.',
     'Pride Edition Sport Band features stripes celebrating the LGBTQ+ community.',
     49.00, None, ['Pride'],
     [], {'compat': 'Apple Watch'}, 2024, ''),
]


# ---------------------------------------------------------------------------
# R2 catalog expansion — adds ~150 more products (watch bands, cases, cables,
# adapters, legacy iPhones/iPads, Vision Pro accessories) to push the catalog
# past 300 SKUs while staying inside the authentic Apple lineup envelope.
# Every tuple here is hand-written + deterministic; no random timestamps,
# no scraped URLs (images point at /static/images/<category>/<slug>.jpg
# which serves a graceful 404 — the agent benchmarks key off text fields).
# ---------------------------------------------------------------------------

def _watch_band_tuple(name, slug, color, price, year, compat='Apple Watch'):
    return (name, slug, 'accessories', 'watch-band', f'{color} band.',
            f'Apple Watch band in {color}. Compatible with {compat}.',
            price, None, [color], [],
            {'compat': compat, 'color': color}, year, '')


def _case_tuple(name, slug, model, color, price, kind='Silicone Case'):
    return (name, slug, 'accessories', 'iphone-case', f'Designed by Apple.',
            f'{kind} for {model} in {color}. MagSafe-compatible.',
            price, None, [color], [],
            {'compat': model, 'color': color, 'kind': kind}, 2024, '')


def _power_tuple(name, slug, watts, color='White', year=2024):
    return (name, slug, 'accessories', 'charger',
            f'{watts}W fast-charge adapter.',
            f'{watts}W USB-C Power Adapter for iPhone, iPad, MacBook. Fast-charge supported.',
            float({20:19,30:39,35:59,67:59,70:59,96:79,140:99}.get(watts, 39)),
            None, [color], [], {'output': f'{watts}W USB-C'}, year, '')


EXTRA_PRODUCTS_R2 = [
    # ------------------------------------------------------------------ Watch
    # Sport Band (41/45/49mm) — color-specific SKUs (real Apple Store layout)
    _watch_band_tuple('Sport Band - 41mm Black',          'sport-band-41mm-black',          'Black',         49.00, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Sport Band - 41mm White',          'sport-band-41mm-white',          'White',         49.00, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Sport Band - 41mm Storm Blue',     'sport-band-41mm-storm-blue',     'Storm Blue',    49.00, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Sport Band - 41mm Plum',           'sport-band-41mm-plum',           'Plum',          49.00, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Sport Band - 41mm Cypress',        'sport-band-41mm-cypress',        'Cypress',       49.00, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Sport Band - 41mm Lake Green',     'sport-band-41mm-lake-green',     'Lake Green',    49.00, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Sport Band - 45mm Black',          'sport-band-45mm-black',          'Black',         49.00, 2024, 'Apple Watch 44/45/46mm'),
    _watch_band_tuple('Sport Band - 45mm White',          'sport-band-45mm-white',          'White',         49.00, 2024, 'Apple Watch 44/45/46mm'),
    _watch_band_tuple('Sport Band - 45mm Storm Blue',     'sport-band-45mm-storm-blue',     'Storm Blue',    49.00, 2024, 'Apple Watch 44/45/46mm'),
    _watch_band_tuple('Sport Band - 45mm Plum',           'sport-band-45mm-plum',           'Plum',          49.00, 2024, 'Apple Watch 44/45/46mm'),
    _watch_band_tuple('Sport Band - 45mm Cypress',        'sport-band-45mm-cypress',        'Cypress',       49.00, 2024, 'Apple Watch 44/45/46mm'),
    _watch_band_tuple('Sport Band - 45mm Denim',          'sport-band-45mm-denim',          'Denim',         49.00, 2024, 'Apple Watch 44/45/46mm'),
    _watch_band_tuple('Sport Band - 49mm Black Ultra',    'sport-band-49mm-black-ultra',    'Black',         49.00, 2024, 'Apple Watch Ultra 49mm'),
    _watch_band_tuple('Sport Band - 49mm Orange Ultra',   'sport-band-49mm-orange-ultra',   'Orange',        49.00, 2024, 'Apple Watch Ultra 49mm'),
    _watch_band_tuple('Sport Band - 49mm Yellow Ultra',   'sport-band-49mm-yellow-ultra',   'Yellow',        49.00, 2024, 'Apple Watch Ultra 49mm'),
    # Sport Loop
    _watch_band_tuple('Sport Loop - 41mm Jet Black',      'sport-loop-41mm-jet-black',      'Jet Black',     49.00, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Sport Loop - 41mm Lake Green',     'sport-loop-41mm-lake-green',     'Lake Green',    49.00, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Sport Loop - 41mm Beige',          'sport-loop-41mm-beige',          'Beige',         49.00, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Sport Loop - 41mm Lavender',       'sport-loop-41mm-lavender',       'Lavender',      49.00, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Sport Loop - 45mm Jet Black',      'sport-loop-45mm-jet-black',      'Jet Black',     49.00, 2024, 'Apple Watch 44/45/46mm'),
    _watch_band_tuple('Sport Loop - 45mm Cerulean',       'sport-loop-45mm-cerulean',       'Cerulean',      49.00, 2024, 'Apple Watch 44/45/46mm'),
    _watch_band_tuple('Sport Loop - 45mm Sage',           'sport-loop-45mm-sage',           'Sage',          49.00, 2024, 'Apple Watch 44/45/46mm'),
    # Braided Solo Loop / Solo Loop
    _watch_band_tuple('Braided Solo Loop - 41mm Charcoal','braided-solo-loop-41mm-charcoal','Charcoal',      99.00, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Braided Solo Loop - 41mm Beige',   'braided-solo-loop-41mm-beige',   'Beige',         99.00, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Braided Solo Loop - 41mm Cerulean','braided-solo-loop-41mm-cerulean','Cerulean',      99.00, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Braided Solo Loop - 45mm Charcoal','braided-solo-loop-45mm-charcoal','Charcoal',      99.00, 2024, 'Apple Watch 44/45/46mm'),
    _watch_band_tuple('Braided Solo Loop - 45mm Beige',   'braided-solo-loop-45mm-beige',   'Beige',         99.00, 2024, 'Apple Watch 44/45/46mm'),
    _watch_band_tuple('Solo Loop - 41mm Black',           'solo-loop-41mm-black',           'Black',         49.00, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Solo Loop - 41mm Storm Blue',      'solo-loop-41mm-storm-blue',      'Storm Blue',    49.00, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Solo Loop - 41mm Red',             'solo-loop-41mm-red',             'Red',           49.00, 2024, 'Apple Watch 40/41mm'),
    # Leather Link / Milanese / Modern Buckle / Nike / Hermes
    _watch_band_tuple('Leather Link - Medium Midnight',   'leather-link-medium-midnight',   'Midnight',      99.00, 2023, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Leather Link - Large Saddle Brown','leather-link-large-saddle-brown','Saddle Brown',  99.00, 2023, 'Apple Watch 44/45/46mm'),
    _watch_band_tuple('Milanese Loop - 41mm Silver',      'milanese-loop-41mm-silver',      'Silver',        99.00, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Milanese Loop - 41mm Graphite',    'milanese-loop-41mm-graphite',    'Graphite',      99.00, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Milanese Loop - 45mm Silver',      'milanese-loop-45mm-silver',      'Silver',        99.00, 2024, 'Apple Watch 44/45/46mm'),
    _watch_band_tuple('Modern Buckle - Medium Black',     'modern-buckle-medium-black',     'Black',         149.00, 2023, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Nike Sport Band - 41mm Black',     'nike-sport-band-41mm-black',     'Black/Volt',    49.00, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Nike Sport Band - 45mm Summit White','nike-sport-band-45mm-summit-white','Summit White', 49.00, 2024, 'Apple Watch 44/45/46mm'),
    _watch_band_tuple('Hermes Single Tour Attelage',      'hermes-single-tour-attelage',    'Noir/Gold',     349.00, 2024, 'Apple Watch Hermes 41mm'),
    _watch_band_tuple('Hermes Single Tour H Pattern',     'hermes-single-tour-h-pattern',   'Noir/Blanc',    389.00, 2024, 'Apple Watch Hermes 45mm'),
    _watch_band_tuple('Ocean Band 49mm Ice Blue',         'ocean-band-49mm-ice-blue',       'Ice Blue',      99.00, 2024, 'Apple Watch Ultra 49mm'),
    _watch_band_tuple('Ocean Band 49mm Deep Orange',      'ocean-band-49mm-deep-orange',    'Deep Orange',   99.00, 2024, 'Apple Watch Ultra 49mm'),

    # ------------------------------------------------------------------ iPhone cases
    _case_tuple('iPhone 17 Pro Silicone Case - Black',          'iphone-17-pro-silicone-case-black',         'iPhone 17 Pro',     'Black',         49.00, 'Silicone Case with MagSafe'),
    _case_tuple('iPhone 17 Pro Silicone Case - Storm Blue',     'iphone-17-pro-silicone-case-storm-blue',    'iPhone 17 Pro',     'Storm Blue',    49.00, 'Silicone Case with MagSafe'),
    _case_tuple('iPhone 17 Pro Silicone Case - Plum',           'iphone-17-pro-silicone-case-plum',          'iPhone 17 Pro',     'Plum',          49.00, 'Silicone Case with MagSafe'),
    _case_tuple('iPhone 17 Pro Silicone Case - Cypress',        'iphone-17-pro-silicone-case-cypress',       'iPhone 17 Pro',     'Cypress',       49.00, 'Silicone Case with MagSafe'),
    _case_tuple('iPhone 17 Pro Silicone Case - Natural Tan',    'iphone-17-pro-silicone-case-natural-tan',   'iPhone 17 Pro',     'Natural Tan',   49.00, 'Silicone Case with MagSafe'),
    _case_tuple('iPhone 17 Silicone Case - Black',              'iphone-17-silicone-case-black',             'iPhone 17',         'Black',         49.00, 'Silicone Case with MagSafe'),
    _case_tuple('iPhone 17 Silicone Case - Storm Blue',         'iphone-17-silicone-case-storm-blue',        'iPhone 17',         'Storm Blue',    49.00, 'Silicone Case with MagSafe'),
    _case_tuple('iPhone 17 Silicone Case - Light Pink',         'iphone-17-silicone-case-light-pink',        'iPhone 17',         'Light Pink',    49.00, 'Silicone Case with MagSafe'),
    _case_tuple('iPhone 17 Silicone Case - Cypress',            'iphone-17-silicone-case-cypress',           'iPhone 17',         'Cypress',       49.00, 'Silicone Case with MagSafe'),
    _case_tuple('iPhone 17 Pro Clear Case with MagSafe',        'iphone-17-pro-clear-case-magsafe',          'iPhone 17 Pro',     'Clear',         49.00, 'Clear Case with MagSafe'),
    _case_tuple('iPhone 16 Pro Silicone Case - Black',          'iphone-16-pro-silicone-case-black',         'iPhone 16 Pro',     'Black',         49.00, 'Silicone Case with MagSafe'),
    _case_tuple('iPhone 16 Pro Silicone Case - Lake Green',     'iphone-16-pro-silicone-case-lake-green',    'iPhone 16 Pro',     'Lake Green',    49.00, 'Silicone Case with MagSafe'),
    _case_tuple('iPhone 16 Fine Woven Case - Natural',          'iphone-16-fine-woven-case-natural',         'iPhone 16',         'Natural',       59.00, 'Fine Woven Case with MagSafe'),
    _case_tuple('iPhone 16 Fine Woven Case - Evergreen',        'iphone-16-fine-woven-case-evergreen',       'iPhone 16',         'Evergreen',     59.00, 'Fine Woven Case with MagSafe'),
    _case_tuple('iPhone 16 Fine Woven Case - Mulberry',         'iphone-16-fine-woven-case-mulberry',        'iPhone 16',         'Mulberry',      59.00, 'Fine Woven Case with MagSafe'),
    _case_tuple('iPhone 15 Leather Case - Midnight',            'iphone-15-leather-case-midnight',           'iPhone 15',         'Midnight',      59.00, 'Leather Case (legacy)'),
    _case_tuple('iPhone 15 Leather Case - Evergreen',           'iphone-15-leather-case-evergreen',          'iPhone 15',         'Evergreen',     59.00, 'Leather Case (legacy)'),
    ('iPhone FineWoven Wallet - Mulberry', 'iphone-finewoven-wallet-mulberry', 'accessories', 'iphone-case',
     'MagSafe-attached card wallet.',
     'FineWoven Wallet attaches magnetically to MagSafe iPhones. Holds up to 3 cards.',
     59.00, None, ['Mulberry'], [], {'features': 'MagSafe, FineWoven'}, 2024, ''),
    ('iPhone FineWoven Wallet - Evergreen', 'iphone-finewoven-wallet-evergreen', 'accessories', 'iphone-case',
     'MagSafe-attached card wallet.',
     'FineWoven Wallet attaches magnetically to MagSafe iPhones. Holds up to 3 cards.',
     59.00, None, ['Evergreen'], [], {'features': 'MagSafe, FineWoven'}, 2024, ''),
    ('iPhone FineWoven Wallet - Twilight', 'iphone-finewoven-wallet-twilight', 'accessories', 'iphone-case',
     'MagSafe-attached card wallet.',
     'FineWoven Wallet attaches magnetically to MagSafe iPhones. Holds up to 3 cards.',
     59.00, None, ['Twilight'], [], {'features': 'MagSafe, FineWoven'}, 2024, ''),

    # ------------------------------------------------------------------ iPad accessories
    ('Magic Keyboard Folio for iPad (10th generation)', 'magic-keyboard-folio-ipad-10', 'accessories', 'ipad-accessory',
     'Two-piece detachable keyboard.',
     'Magic Keyboard Folio for iPad (10th generation) with full-size keys and a trackpad.',
     249.00, None, ['White'], [], {'compat': 'iPad (10th generation)'}, 2022, ''),
    ('Apple Pencil USB-C Charge Cable', 'pencil-usb-c-charge-cable', 'accessories', 'pencil',
     'Charge Apple Pencil (USB-C) and Pencil Pro.',
     'Short USB-C cable for charging Apple Pencil USB-C and Apple Pencil Pro.',
     19.00, None, ['White'], [], {'compat': 'Apple Pencil USB-C / Pro'}, 2023, ''),
    ('Apple Pencil Tips (4 pack)', 'apple-pencil-tip-pack-4', 'accessories', 'pencil',
     'Replacement tips for Apple Pencil.',
     '4-pack of replacement tips for Apple Pencil (1st generation, 2nd generation, Pro).',
     19.00, None, ['White'], [], {'compat': 'Apple Pencil'}, 2018, ''),
    ('Magic Keyboard for iPad Air 11-inch M4 - Black', 'magic-keyboard-ipad-air-11-m4-black', 'accessories', 'ipad-accessory',
     'Floating cantilever design.',
     'Magic Keyboard for iPad Air 11-inch (M4) with backlit keys and trackpad.',
     299.00, None, ['Black'], [], {'compat': 'iPad Air 11-inch (M4)'}, 2024, ''),
    ('Magic Keyboard for iPad Air 13-inch M4 - White', 'magic-keyboard-ipad-air-13-m4-white', 'accessories', 'ipad-accessory',
     'Floating cantilever design.',
     'Magic Keyboard for iPad Air 13-inch (M4) with backlit keys and trackpad.',
     349.00, None, ['White'], [], {'compat': 'iPad Air 13-inch (M4)'}, 2024, ''),

    # ------------------------------------------------------------------ Mac accessories
    ('Magic Mouse (USB-C) - Black',         'magic-mouse-usb-c-black',         'accessories', 'mac-accessory',
     'Multi-Touch surface, USB-C charging.', 'Magic Mouse with Multi-Touch surface in Black. USB-C rechargeable.',
     99.00, None, ['Black'], [], {'features': 'Multi-Touch, USB-C'}, 2024, ''),
    ('Magic Trackpad (USB-C) - Black',      'magic-trackpad-usb-c-black',      'accessories', 'mac-accessory',
     'Force Touch, edge-to-edge glass.', 'Magic Trackpad with Force Touch in Black. USB-C rechargeable.',
     149.00, None, ['Black'], [], {'features': 'Force Touch, USB-C'}, 2024, ''),
    ('Magic Keyboard with Touch ID (USB-C) - Black', 'magic-keyboard-touch-id-usb-c-black', 'accessories', 'mac-accessory',
     'Touch ID, USB-C charging.', 'Magic Keyboard with Touch ID in Black. USB-C rechargeable.',
     129.00, None, ['Black'], [], {'features': 'Touch ID, USB-C'}, 2024, ''),
    ('Magic Keyboard with Touch ID and Numeric Keypad (USB-C) - Black', 'magic-keyboard-touch-id-numeric-usb-c-black', 'accessories', 'mac-accessory',
     'Touch ID, Numeric Keypad, USB-C.', 'Magic Keyboard with Touch ID and Numeric Keypad in Black. USB-C rechargeable.',
     199.00, None, ['Black'], [], {'features': 'Touch ID, Numeric Keypad, USB-C'}, 2024, ''),
    ('Studio Display - Nano-texture Glass', 'studio-display-nano-texture', 'accessories', 'display',
     '27-inch 5K Retina with nano-texture.', '27-inch 5K Retina Studio Display with nano-texture glass for low-glare environments.',
     1899.00, None, ['Silver'], [], {'display': '27" 5K Retina', 'glass': 'Nano-texture'}, 2022, ''),
    ('Studio Display - Tilt and Height Adjustable Stand', 'studio-display-tilt-height-stand', 'accessories', 'display',
     'Counterbalanced tilt + height.', 'Studio Display with tilt and height-adjustable stand. Standard glass.',
     1999.00, None, ['Silver'], [], {'stand': 'Tilt and Height Adjustable'}, 2022, ''),
    ('Pro Display XDR Pro Stand',           'pro-display-pro-stand',           'accessories', 'display',
     'Counterbalanced arm for Pro Display XDR.', 'Optional Pro Stand for Pro Display XDR providing tilt, rotation, height adjustment, and portrait mode.',
     999.00, None, ['Silver'], [], {'compat': 'Pro Display XDR'}, 2019, ''),
    ('Pro Display VESA Mount Adapter',      'pro-display-vesa-mount-adapter',  'accessories', 'display',
     'VESA mount for Pro Display XDR / Studio Display.', 'VESA Mount Adapter attaches Pro Display XDR or Studio Display to a third-party VESA arm.',
     199.00, None, ['Silver'], [], {'compat': 'Pro Display XDR, Studio Display'}, 2019, ''),

    # ------------------------------------------------------------------ Cables / Adapters / Power
    ('USB-C to 3.5 mm Headphone Jack Adapter', 'usb-c-to-3-5mm-jack-adapter', 'accessories', 'cable',
     'Listen with 3.5 mm headphones.',
     'Connect 3.5 mm headphones to a USB-C device. Supports stereo audio in and out.',
     9.00, None, ['White'], [], {'features': '3.5 mm jack'}, 2018, ''),
    ('Lightning to 3.5 mm Headphone Jack Adapter', 'lightning-to-3-5mm-jack-adapter', 'accessories', 'cable',
     'Listen with 3.5 mm headphones.',
     'Connect 3.5 mm headphones to a Lightning device.',
     9.00, None, ['White'], [], {'features': '3.5 mm jack'}, 2016, ''),
    ('USB-C VGA Multiport Adapter',     'usb-c-vga-multiport-adapter',   'accessories', 'cable',
     'VGA, USB-A and USB-C charging.',
     'Connect a VGA display, a USB-A device, and a USB-C power adapter at the same time.',
     69.00, None, ['White'], [], {'features': 'VGA + USB-A + USB-C PD'}, 2018, ''),
    ('USB-C Digital AV Multiport Adapter', 'usb-c-digital-av-multiport', 'accessories', 'cable',
     'HDMI 4K, USB-A and USB-C charging.',
     'Connect an HDMI display (up to 4K@60Hz with HDR), a USB-A device, and a USB-C power adapter.',
     69.00, None, ['White'], [], {'features': 'HDMI 4K + USB-A + USB-C PD'}, 2022, ''),
    ('USB-C to USB Adapter',            'usb-c-to-usb-adapter',          'accessories', 'cable',
     'Use USB-A peripherals.',
     'Connect a USB-A device such as a flash drive, camera, or hub to a USB-C Mac.',
     19.00, None, ['White'], [], {'features': 'USB-A to USB-C'}, 2017, ''),
    ('USB-C to SD Card Reader',         'usb-c-to-sd-card-reader',       'accessories', 'cable',
     'Read SD cards at UHS-II speeds.',
     'USB-C SD Card Reader supports SD UHS-II cards at up to 312 MB/s.',
     39.00, None, ['White'], [], {'features': 'UHS-II 312 MB/s'}, 2017, ''),
    ('USB-C Charge Cable (1m)',         'usb-c-charge-cable-1m',         'accessories', 'cable',
     'Charge USB-C devices.',
     '1-metre USB-C Charge Cable for iPad, MacBook and other USB-C devices.',
     19.00, None, ['White'], [], {'features': 'USB-C charging'}, 2019, ''),
    ('USB-C to MagSafe 3 Cable (1m) - Silver', 'usb-c-magsafe-3-cable-1m-silver', 'accessories', 'cable',
     'Quick-release MagSafe charging.',
     '1-metre USB-C to MagSafe 3 Cable in Silver for MacBook Pro and MacBook Air.',
     49.00, None, ['Silver'], [], {'features': 'MagSafe 3 fast-charging'}, 2024, ''),
    ('Thunderbolt 5 Pro Cable (1m)',    'thunderbolt-5-pro-cable-1m',    'accessories', 'cable',
     'Up to 120 Gb/s.',
     'Thunderbolt 5 Pro Cable supports up to 120 Gb/s and 240W charging.',
     129.00, None, ['Space Black'], [], {'features': '120 Gb/s, 240W'}, 2024, ''),
    ('Thunderbolt 4 Pro Cable (3m)',    'thunderbolt-4-pro-cable-3m',    'accessories', 'cable',
     'Up to 40 Gb/s data transfer.',
     '3-metre Thunderbolt 4 Pro Cable supports up to 40 Gb/s and 100W charging.',
     159.00, None, ['Space Black'], [], {'features': '40 Gb/s, 100W'}, 2022, ''),
    ('HDMI to HDMI Cable (2m)',         'hdmi-cable-2m',                 'accessories', 'cable',
     '4K HDR-ready HDMI cable.',
     '2-metre HDMI cable supports 4K@60Hz with HDR. Compatible with Apple TV 4K and Mac.',
     29.00, None, ['Black'], [], {'features': 'HDMI 2.1, 4K HDR'}, 2024, ''),
    ('MagSafe Charger (2m)',            'magsafe-charger-2m',            'accessories', 'charger',
     'Longer MagSafe cable.',
     '2-metre MagSafe Charger delivers up to 25W fast-charge to compatible iPhones.',
     45.00, None, ['White'], [], {'features': 'MagSafe 25W'}, 2024, ''),
    ('MagSafe Battery Pack',            'magsafe-battery-pack',          'accessories', 'charger',
     'On-the-go MagSafe charging.',
     'Snap-on MagSafe Battery Pack. Up to 70% of additional charge on iPhone.',
     99.00, None, ['White'], [], {'features': 'MagSafe, 1460 mAh'}, 2021, ''),
    ('MagSafe Duo Charger',             'magsafe-duo-charger-2',         'accessories', 'charger',
     'Charge iPhone and Apple Watch.',
     'Folding MagSafe Duo Charger with USB-C cable. Charges iPhone and Apple Watch simultaneously.',
     129.00, None, ['White'], [], {'features': 'MagSafe + Watch'}, 2020, ''),
    ('MagSafe Charger (3-in-1)',        'magsafe-charger-3-in-1',        'accessories', 'charger',
     'iPhone + Apple Watch + AirPods.',
     'New 3-in-1 MagSafe puck charges iPhone (25W), Apple Watch, and AirPods at the same time.',
     149.00, None, ['White'], [], {'features': 'MagSafe + Watch + AirPods'}, 2025, ''),
    _power_tuple('30W USB-C Power Adapter',  'usb-c-power-adapter-30w', 30),
    _power_tuple('35W USB-C Dual Power Adapter', 'usb-c-power-adapter-35w-dual', 35),
    _power_tuple('67W USB-C Power Adapter',  'usb-c-power-adapter-67w', 67),
    _power_tuple('70W USB-C Power Adapter',  'usb-c-power-adapter-70w', 70),
    _power_tuple('96W USB-C Power Adapter',  'usb-c-power-adapter-96w', 96),
    _power_tuple('140W USB-C Power Adapter', 'usb-c-power-adapter-140w', 140),

    # ------------------------------------------------------------------ AirPods accessories
    ('AirPods Pro Tip Kit (XS, S, M, L)', 'airpods-pro-tip-kit', 'accessories', 'airpods-case',
     'Replacement silicone tips.', 'Replacement silicone ear tips for AirPods Pro 2 / 3. Includes XS, S, M, L.',
     9.00, None, ['White'], [], {'compat': 'AirPods Pro 2 / 3'}, 2022, ''),
    ('AirPods Max Smart Case',          'airpods-max-smart-case',        'accessories', 'airpods-case',
     'Slim, soft case.', 'AirPods Max Smart Case puts AirPods Max into a low-power state to preserve battery.',
     59.00, None, ['Midnight', 'Starlight', 'Orange', 'Purple'], [], {'compat': 'AirPods Max'}, 2024, ''),
    ('AirPods Max Replacement Ear Cushions - Midnight', 'airpods-max-replacement-cushions-midnight', 'accessories', 'airpods-case',
     'Magnetically attached cushions.', 'Replacement Ear Cushions for AirPods Max in Midnight.',
     69.00, None, ['Midnight'], [], {'compat': 'AirPods Max'}, 2024, ''),
    ('AirPods Pro MagSafe Charging Case (spare)', 'airpods-pro-magsafe-case-spare', 'accessories', 'airpods-case',
     'Replacement MagSafe charging case.', 'Spare MagSafe Charging Case for AirPods Pro 2.',
     99.00, None, ['White'], [], {'compat': 'AirPods Pro 2'}, 2022, ''),

    # ------------------------------------------------------------------ HomePod / Apple TV / Siri Remote
    ('Siri Remote (3rd generation)',    'siri-remote-3rd-gen',           'accessories', 'tv-accessory',
     'Touch-enabled clickpad, USB-C.', 'Siri Remote (3rd generation) with USB-C charging port for Apple TV 4K.',
     69.00, None, ['Silver'], [], {'compat': 'Apple TV 4K (2022 / 2024)'}, 2024, ''),
    ('Siri Remote (2nd generation)',    'siri-remote-2nd-gen',           'accessories', 'tv-accessory',
     'Touch-enabled clickpad, Lightning.', 'Siri Remote (2nd generation) with Lightning port for Apple TV 4K (2021).',
     59.00, None, ['Silver'], [], {'compat': 'Apple TV 4K (2021)'}, 2021, ''),

    # ------------------------------------------------------------------ AirTag bundles + accessories
    ('AirTag (4 pack)',                 'airtag-4-pack',                 'accessories', 'airtag',
     'Find your stuff.', 'AirTag 4-pack to attach to keys, bags, and more. Find via the Find My network.',
     99.00, None, ['White'], [], {'features': 'Find My, Precision Finding'}, 2021, ''),
    ('AirTag Leather Loop - Saddle Brown', 'airtag-loop-saddle-brown',   'accessories', 'airtag',
     'Designed by Apple.', 'AirTag Leather Loop in Saddle Brown.',
     39.00, None, ['Saddle Brown'], [], {'compat': 'AirTag'}, 2021, ''),
    ('AirTag Leather Loop - Midnight',  'airtag-loop-midnight',          'accessories', 'airtag',
     'Designed by Apple.', 'AirTag Leather Loop in Midnight.',
     39.00, None, ['Midnight'], [], {'compat': 'AirTag'}, 2021, ''),
    ('AirTag Polyurethane Keyring',     'airtag-keyring-polyurethane',   'accessories', 'airtag',
     'Designed by Apple.', 'AirTag Polyurethane Keyring in White.',
     35.00, None, ['White'], [], {'compat': 'AirTag'}, 2021, ''),

    # ------------------------------------------------------------------ Vision Pro accessories
    ('Apple Vision Pro Cover',          'apple-vision-pro-cover',        'accessories', 'vision-pro-accessory',
     'Soft protective front cover.', 'Magnetically attached cover protects the front glass of Apple Vision Pro during storage.',
     199.00, None, ['Light Gray'], [], {'compat': 'Apple Vision Pro'}, 2024, ''),
    ('Apple Vision Pro Solo Knit Band - Medium', 'apple-vision-pro-solo-knit-band-medium', 'accessories', 'vision-pro-accessory',
     'Single-piece knit band.', 'Replacement Solo Knit Band for Apple Vision Pro - Medium.',
     99.00, None, ['Black'], [], {'compat': 'Apple Vision Pro', 'size': 'Medium'}, 2024, ''),
    ('Apple Vision Pro Dual Loop Band - Medium', 'apple-vision-pro-dual-loop-band-medium', 'accessories', 'vision-pro-accessory',
     'Upper and lower straps.', 'Replacement Dual Loop Band for Apple Vision Pro - Medium.',
     99.00, None, ['Black'], [], {'compat': 'Apple Vision Pro', 'size': 'Medium'}, 2024, ''),
    ('ZEISS Optical Inserts - Readers', 'zeiss-optical-inserts-readers', 'accessories', 'vision-pro-accessory',
     'Reading-strength magnetic lenses.', 'ZEISS Optical Inserts (Readers, +0.25 to +3.50) for Apple Vision Pro.',
     99.00, None, ['Clear'], [], {'compat': 'Apple Vision Pro'}, 2024, ''),
    ('ZEISS Optical Inserts - Prescription', 'zeiss-optical-inserts-prescription', 'accessories', 'vision-pro-accessory',
     'Custom prescription magnetic lenses.', 'ZEISS Optical Inserts (Prescription, sphere -10.00 to +6.00) for Apple Vision Pro. Prescription required.',
     149.00, None, ['Clear'], [], {'compat': 'Apple Vision Pro'}, 2024, ''),
    ('Apple Vision Pro Developer Strap', 'apple-vision-pro-developer-strap', 'accessories', 'vision-pro-accessory',
     'USB-C connection for developers.', 'Apple Vision Pro Developer Strap provides a USB-C connection for app development and accessory testing.',
     299.00, None, ['Gray'], [], {'compat': 'Apple Vision Pro'}, 2024, ''),

    # ------------------------------------------------------------------ AppleCare variants
    ('AppleCare+ for iPhone (2-year)',  'applecare-iphone-2yr',          'accessories', 'care',
     '2 years of expert support.', 'AppleCare+ for iPhone with up to two incidents of accidental damage protection every 12 months.',
     199.00, None, [], [], {'duration': '2 years', 'incidents': 'Unlimited @ service fee'}, 2024, ''),
    ('AppleCare+ for Apple Watch (2-year)', 'applecare-watch-2yr',        'accessories', 'care',
     '2 years of expert support.', 'AppleCare+ for Apple Watch with up to two incidents of accidental damage protection every 12 months.',
     59.00, None, [], [], {'duration': '2 years', 'incidents': 'Unlimited @ service fee'}, 2024, ''),
    ('AppleCare+ for AirPods (2-year)', 'applecare-airpods-2yr',         'accessories', 'care',
     '2 years of expert support.', 'AppleCare+ for AirPods with up to two incidents of accidental damage protection every 12 months.',
     29.00, None, [], [], {'duration': '2 years', 'incidents': 'Unlimited @ service fee'}, 2024, ''),
    ('AppleCare+ for iPad (2-year)',    'applecare-ipad-2yr',            'accessories', 'care',
     '2 years of expert support.', 'AppleCare+ for iPad with up to two incidents of accidental damage protection every 12 months.',
     99.00, None, [], [], {'duration': '2 years', 'incidents': 'Unlimited @ service fee'}, 2024, ''),
    ('AppleCare+ for Apple Vision Pro (2-year)', 'applecare-vision-pro-2yr', 'accessories', 'care',
     '2 years of expert support.', 'AppleCare+ for Apple Vision Pro with up to two incidents of accidental damage protection every 12 months.',
     499.00, None, [], [], {'duration': '2 years', 'incidents': 'Unlimited @ service fee'}, 2024, ''),

    # ------------------------------------------------------------------ Watch chargers
    ('Apple Watch Magnetic Fast Charger to USB-C Cable (1m)', 'apple-watch-magnetic-fast-charger-1m', 'accessories', 'watch-accessory',
     'Fast-charge Apple Watch.', 'Fast-charge Apple Watch Series 7 and later. 1m USB-C cable.',
     29.00, None, ['White'], [], {'compat': 'Apple Watch Series 7+', 'fast_charge': True}, 2022, ''),
    ('Apple Watch Magnetic Charging Cable (2m)', 'apple-watch-magnetic-charging-2m', 'accessories', 'watch-accessory',
     'Magnetic charging cable.', 'Apple Watch Magnetic Charging Cable, 2 metres.',
     35.00, None, ['White'], [], {'compat': 'Apple Watch'}, 2020, ''),

    # ------------------------------------------------------------------ Legacy iPhones (trade-in story)
    ('iPhone X', 'iphone-x', 'iphone', '', 'Say hello to the future.',
     'A11 Bionic chip, 5.8-inch Super Retina OLED display, Face ID, dual 12MP cameras.',
     349.00, None, ['Silver', 'Space Gray'], ['64GB', '256GB'],
     {'chip': 'A11 Bionic', 'display': '5.8" Super Retina OLED'}, 2017, 'A11 Bionic'),
    ('iPhone 8', 'iphone-8', 'iphone', '', 'A new generation of iPhone.',
     'A11 Bionic chip, 4.7-inch Retina HD display, wireless charging.',
     249.00, None, ['Space Gray', 'Silver', 'Gold', 'Red'], ['64GB', '128GB', '256GB'],
     {'chip': 'A11 Bionic', 'display': '4.7" Retina HD'}, 2017, 'A11 Bionic'),
    ('iPhone 8 Plus', 'iphone-8-plus', 'iphone', '', 'A new generation of iPhone.',
     'A11 Bionic chip, 5.5-inch Retina HD display, dual 12MP cameras.',
     299.00, None, ['Space Gray', 'Silver', 'Gold', 'Red'], ['64GB', '128GB', '256GB'],
     {'chip': 'A11 Bionic', 'display': '5.5" Retina HD'}, 2017, 'A11 Bionic'),
    ('iPhone 7', 'iphone-7', 'iphone', '', 'This is iPhone 7.',
     'A10 Fusion chip, 4.7-inch Retina HD, water resistant, 12MP camera.',
     199.00, None, ['Black', 'Silver', 'Gold', 'Rose Gold', 'Red'], ['32GB', '128GB', '256GB'],
     {'chip': 'A10 Fusion', 'display': '4.7" Retina HD'}, 2016, 'A10 Fusion'),
    ('iPhone 7 Plus', 'iphone-7-plus', 'iphone', '', 'This is iPhone 7 Plus.',
     'A10 Fusion chip, 5.5-inch Retina HD, dual 12MP cameras, water resistant.',
     249.00, None, ['Black', 'Silver', 'Gold', 'Rose Gold', 'Red'], ['32GB', '128GB', '256GB'],
     {'chip': 'A10 Fusion', 'display': '5.5" Retina HD'}, 2016, 'A10 Fusion'),

    # ------------------------------------------------------------------ Legacy iPads
    ('iPad (8th generation)', 'ipad-8', 'ipad', '', 'Just what you need. In an iPad.',
     'A12 Bionic chip, 10.2-inch Retina display, Apple Pencil (1st gen) support.',
     299.00, None, ['Space Gray', 'Silver', 'Gold'], ['32GB', '128GB'],
     {'chip': 'A12 Bionic', 'display': '10.2" Retina'}, 2020, 'A12 Bionic'),
    ('iPad (7th generation)', 'ipad-7', 'ipad', '', 'Just what you need.',
     'A10 Fusion chip, 10.2-inch Retina display, Smart Connector.',
     249.00, None, ['Space Gray', 'Silver', 'Gold'], ['32GB', '128GB'],
     {'chip': 'A10 Fusion', 'display': '10.2" Retina'}, 2019, 'A10 Fusion'),
    ('iPad Air (5th generation)', 'ipad-air-5', 'ipad', 'ipad-air', 'Light. Bright. Full of might.',
     'Apple M1 chip, 10.9-inch Liquid Retina display, USB-C.',
     499.00, None, ['Space Gray', 'Starlight', 'Pink', 'Purple', 'Blue'], ['64GB', '256GB'],
     {'chip': 'M1', 'display': '10.9" Liquid Retina'}, 2022, 'M1'),
    ('iPad Air (4th generation)', 'ipad-air-4', 'ipad', 'ipad-air', 'Power. It is in the Air.',
     'A14 Bionic chip, 10.9-inch Liquid Retina display, USB-C.',
     449.00, None, ['Silver', 'Space Gray', 'Rose Gold', 'Green', 'Sky Blue'], ['64GB', '256GB'],
     {'chip': 'A14 Bionic', 'display': '10.9" Liquid Retina'}, 2020, 'A14 Bionic'),
    ('iPad mini (5th generation)', 'ipad-mini-5', 'ipad', 'ipad-mini', 'Mega power. Mini sized.',
     'A12 Bionic chip, 7.9-inch Retina display, Apple Pencil (1st gen) support.',
     349.00, None, ['Silver', 'Space Gray', 'Gold'], ['64GB', '256GB'],
     {'chip': 'A12 Bionic', 'display': '7.9" Retina'}, 2019, 'A12 Bionic'),

    # ------------------------------------------------------------------ Legacy Mac
    ('Mac mini (M2)', 'mac-mini-m2', 'mac', 'mac-mini', 'More mini. More mighty.',
     'Apple M2 chip, up to 24GB unified memory, two USB-C / Thunderbolt 4 ports.',
     599.00, 24.95, ['Silver'], ['256GB', '512GB', '1TB', '2TB'],
     {'chip': 'M2', 'memory': '8GB / 16GB / 24GB'}, 2023, 'M2'),
    ('MacBook Pro 13-inch (M1)', 'macbook-pro-13-m1', 'mac', 'macbook-pro', 'Power to go.',
     'Apple M1 chip, 13.3-inch Retina display, Touch Bar.',
     1099.00, 45.79, ['Space Gray', 'Silver'], ['256GB', '512GB'],
     {'chip': 'M1', 'display': '13.3" Retina'}, 2020, 'M1'),

    # ------------------------------------------------------------------ Legacy Watch
    ('Apple Watch Series 5', 'apple-watch-series-5', 'watch', '', 'See it. Even when you do not raise it.',
     'S5 SiP, Always-On Retina display, ECG, fall detection.',
     179.00, None, ['Space Gray', 'Silver', 'Gold'], ['40mm', '44mm'],
     {'chip': 'S5', 'display': 'Always-On Retina'}, 2019, ''),
    ('Apple Watch Series 4', 'apple-watch-series-4', 'watch', '', 'A breakthrough in health.',
     'S4 SiP, ECG, fall detection, larger 40 / 44mm display.',
     149.00, None, ['Space Gray', 'Silver', 'Gold'], ['40mm', '44mm'],
     {'chip': 'S4', 'display': 'Retina LTPO OLED'}, 2018, ''),
    ('Apple Watch Series 3', 'apple-watch-series-3', 'watch', '', 'A healthy leap ahead.',
     'S3 SiP, GPS + Cellular options.',
     129.00, None, ['Space Gray', 'Silver'], ['38mm', '42mm'],
     {'chip': 'S3', 'display': 'Retina'}, 2017, ''),

    # ------------------------------------------------------------------ Legacy AirPods
    ('AirPods (2nd generation)', 'airpods-2nd-gen', 'airpods', '', 'Wireless. Effortless. Magical.',
     'H1 chip, hands-free Hey Siri, wireless charging case option.',
     129.00, None, ['White'], [],
     {'chip': 'H1', 'battery': '24 hr with case'}, 2019, ''),
    ('AirPods Pro (1st generation)', 'airpods-pro-1st-gen', 'airpods', '', 'Magic like you have never heard.',
     'H1 chip, Active Noise Cancellation, Transparency mode, sweat and water resistant.',
     199.00, None, ['White'], [],
     {'chip': 'H1', 'features': 'ANC, Transparency'}, 2019, ''),

    # ------------------------------------------------------------------ Final padding (push catalog past 300)
    ('Apple TV (3rd generation)', 'apple-tv-3rd-gen', 'tv', '', 'A small device with a big idea.',
     'A5 chip, 1080p HD output via HDMI (legacy).',
     99.00, None, ['Black'], [],
     {'chip': 'A5', 'output': '1080p HD'}, 2012, ''),
    ('HomePod (1st generation, Space Gray)', 'homepod-1st-gen-space-gray', 'homepod', '', 'A breakthrough in sound.',
     'A8 chip, seven tweeter array, room-sensing spatial awareness (legacy).',
     299.00, None, ['Space Gray'], [],
     {'chip': 'A8'}, 2018, ''),
    ('Beats Powerbeats Pro', 'beats-powerbeats-pro', 'audio', '', 'Run, gym, anywhere.',
     'H1 chip, ear-hook design, sweat-resistant, 9 hours of listening time.',
     199.99, None, ['Black', 'Ivory', 'Moss', 'Navy'], [],
     {'chip': 'H1', 'battery': '9 hr'}, 2019, ''),
    ('Beats Flex', 'beats-flex', 'audio', '', 'Wireless. Affordable. All-day.',
     'Apple W1 chip, magnetic earbuds, 12 hours of listening time.',
     49.99, None, ['Beats Black', 'Yuzu Yellow', 'Smoke Gray', 'Flame Blue'], [],
     {'chip': 'W1', 'battery': '12 hr'}, 2020, ''),
    ('Smart Folio for iPad Air 13-inch (M4) - Light Violet', 'smart-folio-ipad-air-13-m4-light-violet', 'accessories', 'ipad-accessory',
     'Front and back protection.',
     'Polyurethane Smart Folio for iPad Air 13-inch (M4) in Light Violet.',
     79.00, None, ['Light Violet'], [], {'compat': 'iPad Air 13-inch (M4)'}, 2024, ''),
    ('Smart Folio for iPad Air 13-inch (M4) - Charcoal Gray', 'smart-folio-ipad-air-13-m4-charcoal-gray', 'accessories', 'ipad-accessory',
     'Front and back protection.',
     'Polyurethane Smart Folio for iPad Air 13-inch (M4) in Charcoal Gray.',
     79.00, None, ['Charcoal Gray'], [], {'compat': 'iPad Air 13-inch (M4)'}, 2024, ''),
    ('Smart Folio for iPad mini 7 - Sage', 'smart-folio-ipad-mini-7-sage', 'accessories', 'ipad-accessory',
     'Front and back protection.',
     'Polyurethane Smart Folio for iPad mini 7 in Sage.',
     59.00, None, ['Sage'], [], {'compat': 'iPad mini 7'}, 2024, ''),
    ('Polishing Cloth (extra)', 'polishing-cloth-extra', 'accessories', '',
     'Soft, nonabrasive cloth.',
     'Polishing Cloth made of soft nonabrasive material cleans any Apple display, including nano-texture glass.',
     19.00, None, ['White'], [], {'features': 'nano-texture safe'}, 2021, ''),
    ('World Travel Adapter Kit (2025)', 'world-travel-adapter-kit-2025', 'accessories', 'charger',
     'Charge anywhere.',
     'World Travel Adapter Kit includes plug attachments for North America, EU, UK, AU, China, Japan, Korea, Hong Kong, and Brazil.',
     29.00, None, ['White'], [], {'features': '8 plug heads'}, 2025, ''),
    ('iPhone Lightning Dock', 'iphone-lightning-dock', 'accessories', 'charger',
     'Charge and sync at the desk.',
     'Lightning Dock for iPhone holds and charges iPhone upright while syncing.',
     49.00, None, ['White'], [], {'features': 'Lightning'}, 2016, ''),
    ('USB-C to Lightning Adapter', 'usb-c-to-lightning-adapter', 'accessories', 'cable',
     'Connect Lightning accessories.',
     'USB-C to Lightning Adapter lets Lightning accessories such as EarPods or older docks connect to USB-C iPads and Macs.',
     35.00, None, ['White'], [], {'features': 'Lightning to USB-C'}, 2023, ''),
    ('Beats Pill+ (Legacy)', 'beats-pill-plus-legacy', 'audio', '', 'Portable stereo speaker.',
     'Beats Pill+ portable Bluetooth speaker with 12-hour battery (legacy 2015 design).',
     179.95, None, ['Black', 'White', 'Red'], [],
     {'features': 'Bluetooth, 12 hr'}, 2015, ''),
]


# ---------------------------------------------------------------------------
# R3 catalog expansion — pushes total SKU count past 600.
# Coverage: Apple software services (Music/TV+/iCloud+/Arcade/Fitness+/News+/
# Apple One/AppleCare+), Beats line color variants, Mac peripherals (Magic
# Mouse/Trackpad/Keyboard, Studio Display variants), iPad Smart Folio + Magic
# Keyboard per model, iPhone 17 series cases + wallets + crossbody straps,
# additional Watch bands (Trail Loop, Alpine Loop, Ocean, Hermès, Nike, Modern
# Buckle, Braided Solo Loop), chargers / cables / adapters, HomeKit accessories.
# Every tuple is deterministic; new "service" subcategory introduced for the
# subscription SKUs (price = monthly headline).
# ---------------------------------------------------------------------------

def _service_tuple(name, slug, price, period, desc, year=2025, subcat='service'):
    """Subscription SKU: stored in category=accessories, subcategory=service so
    the rest of the catalog UI keeps working. Price is the headline period
    price (e.g. monthly individual = 10.99)."""
    return (name, slug, 'accessories', subcat,
            f'{period} membership.',
            desc, float(price), None, [], [],
            {'period': period, 'kind': 'subscription'}, year, '')


def _care_tuple(name, slug, device, price, term='2-year', desc=None):
    desc = desc or (f'AppleCare+ for {device} extends hardware coverage with unlimited '
                    f'incidents of accidental damage, priority access to Apple experts, '
                    f'and battery service. {term} term.')
    return (name, slug, 'accessories', 'applecare',
            f'AppleCare+ for {device}.',
            desc, float(price), None, [], [],
            {'compat': device, 'term': term, 'kind': 'applecare'}, 2025, '')


def _homekit_tuple(name, slug, brand, kind, price, year, summary):
    return (name, slug, 'accessories', 'homekit',
            f'Works with Apple Home.', summary,
            float(price), None, [], [],
            {'brand': brand, 'kind': kind, 'works_with': 'Apple Home, Siri'}, year, '')


def _adapter_tuple(name, slug, port_in, port_out, length, price, year=2024):
    desc = (f'Apple {name}. Connects {port_in} to {port_out}. Length: {length}. '
            f'Compatible with iPhone, iPad, and Mac models with the corresponding port.')
    return (name, slug, 'accessories', 'cable',
            f'{port_in} to {port_out}.', desc,
            float(price), None, ['White'], [],
            {'in': port_in, 'out': port_out, 'length': length}, year, '')


def _smart_folio_tuple(name, slug, ipad_model, color, price, year=2024):
    desc = (f'Smart Folio for {ipad_model} in {color}. Snaps on with magnets, '
            f'doubles as a stand for typing and viewing, and wakes the iPad on open.')
    return (name, slug, 'accessories', 'ipad-accessory',
            f'Smart Folio for {ipad_model}.', desc,
            float(price), None, [color], [],
            {'compat': ipad_model, 'color': color, 'kind': 'Smart Folio'}, year, '')


def _magic_kbd_ipad_tuple(name, slug, ipad_model, color, price, year=2024):
    desc = (f'Magic Keyboard for {ipad_model} in {color}. Floating cantilever design, '
            f'glass trackpad, function row, backlit keys, USB-C passthrough charging.')
    return (name, slug, 'accessories', 'ipad-accessory',
            f'Magic Keyboard for {ipad_model}.', desc,
            float(price), None, [color], [],
            {'compat': ipad_model, 'color': color, 'kind': 'Magic Keyboard'}, year, '')


def _crossbody_tuple(color, price=59.0):
    slug = f'iphone-crossbody-strap-{color.lower().replace(" ", "-")}'
    return ('iPhone Crossbody Strap - ' + color, slug, 'accessories', 'iphone-case',
            'Wear it. Carry it.',
            f'iPhone Crossbody Strap in {color}. Magnetic, adjustable, MagSafe-compatible.',
            59.0, None, [color], [],
            {'kind': 'Crossbody Strap', 'color': color}, 2025, '')


EXTRA_PRODUCTS_R3 = [
    # ------------------------------------------------------------ Subscriptions
    _service_tuple('Apple Music Individual', 'apple-music-individual',  10.99, 'monthly',
                   'Listen to over 100 million songs ad-free, Spatial Audio with Dolby Atmos, lossless audio, and 30,000+ expert-curated playlists.'),
    _service_tuple('Apple Music Family',     'apple-music-family',      16.99, 'monthly',
                   'Apple Music for up to 6 family members. Includes personal libraries, recommendations, Apple Music Kids, and parental controls.'),
    _service_tuple('Apple Music Student',    'apple-music-student',      5.99, 'monthly',
                   'Apple Music for verified college students at a reduced rate. Includes Apple TV+ at no extra cost.'),
    _service_tuple('Apple Music Voice',      'apple-music-voice',        4.99, 'monthly',
                   'Apple Music for Siri. Stream over 100 million songs hands-free on iPhone, HomePod, and CarPlay.'),
    _service_tuple('Apple TV+',              'apple-tv-plus',            9.99, 'monthly',
                   'Award-winning Apple Originals — drama, comedy, kids and family, documentary, and more. 4K HDR, Dolby Vision, Dolby Atmos.'),
    _service_tuple('iCloud+ 50GB',           'icloud-50gb',              0.99, 'monthly',
                   'iCloud+ with 50GB storage, Private Relay, Hide My Email, Custom Email Domain, and HomeKit Secure Video for one camera.'),
    _service_tuple('iCloud+ 200GB',          'icloud-200gb',             2.99, 'monthly',
                   'iCloud+ with 200GB storage. All iCloud+ features. Sharable with up to 5 family members.'),
    _service_tuple('iCloud+ 2TB',            'icloud-2tb',               9.99, 'monthly',
                   'iCloud+ with 2TB storage. HomeKit Secure Video supports up to 5 cameras. Sharable with up to 5 family members.'),
    _service_tuple('iCloud+ 6TB',            'icloud-6tb',              29.99, 'monthly',
                   'iCloud+ with 6TB storage. Best for ProRes, ProRAW, and large libraries. HomeKit Secure Video unlimited cameras.'),
    _service_tuple('iCloud+ 12TB',           'icloud-12tb',             59.99, 'monthly',
                   'iCloud+ with 12TB storage. Maximum capacity available. Sharable with up to 5 family members.'),
    _service_tuple('Apple Arcade',           'apple-arcade',             6.99, 'monthly',
                   'Apple Arcade gives you unlimited access to a growing collection of more than 200 incredibly fun games — no ads, no in-app purchases.'),
    _service_tuple('Apple Fitness+',         'apple-fitness-plus',       9.99, 'monthly',
                   'Apple Fitness+ studio-style workouts and meditations with the world\'s top trainers. Stream on iPhone, iPad, or Apple TV.'),
    _service_tuple('Apple News+',            'apple-news-plus',         12.99, 'monthly',
                   'Apple News+ unlocks hundreds of magazines, leading newspapers, premium digital publishers, audio stories, puzzles, and more.'),
    _service_tuple('Apple One Individual',   'apple-one-individual',    19.95, 'monthly',
                   'Apple One bundles Apple Music, Apple TV+, Apple Arcade, and 50GB of iCloud+ for one low monthly price.'),
    _service_tuple('Apple One Family',       'apple-one-family',        25.95, 'monthly',
                   'Apple One Family bundles Apple Music, Apple TV+, Apple Arcade, and 200GB of iCloud+ for up to 6 family members.'),
    _service_tuple('Apple One Premier',      'apple-one-premier',       37.95, 'monthly',
                   'Apple One Premier bundles Apple Music, Apple TV+, Apple Arcade, Apple News+, Apple Fitness+, and 2TB of iCloud+ for up to 6 family members.'),

    # ------------------------------------------------------------ AppleCare+
    _care_tuple('AppleCare+ for iPhone 17 Pro',      'applecare-iphone-17-pro',      'iPhone 17 Pro',      8.99,  '2-year'),
    _care_tuple('AppleCare+ for iPhone 17 Pro Max',  'applecare-iphone-17-pro-max',  'iPhone 17 Pro Max',  9.99,  '2-year'),
    _care_tuple('AppleCare+ for iPhone Air',         'applecare-iphone-air',         'iPhone Air',         8.49,  '2-year'),
    _care_tuple('AppleCare+ for iPhone 17',          'applecare-iphone-17',          'iPhone 17',          7.99,  '2-year'),
    _care_tuple('AppleCare+ for iPhone 17e',         'applecare-iphone-17e',         'iPhone 17e',         6.99,  '2-year'),
    _care_tuple('AppleCare+ with Theft and Loss for iPhone 17 Pro',     'applecare-tnl-iphone-17-pro',     'iPhone 17 Pro',     13.49, '2-year',
                desc='AppleCare+ with Theft and Loss extends coverage to include theft or loss, plus unlimited accidental damage incidents and 24/7 priority support.'),
    _care_tuple('AppleCare+ for Mac (13-inch MacBook Air)',  'applecare-macbook-air-13',  'MacBook Air 13"',  8.99,  '3-year'),
    _care_tuple('AppleCare+ for Mac (15-inch MacBook Air)',  'applecare-macbook-air-15',  'MacBook Air 15"', 10.99,  '3-year'),
    _care_tuple('AppleCare+ for MacBook Pro 14-inch',        'applecare-macbook-pro-14',  'MacBook Pro 14"', 14.99,  '3-year'),
    _care_tuple('AppleCare+ for MacBook Pro 16-inch',        'applecare-macbook-pro-16',  'MacBook Pro 16"', 16.99,  '3-year'),
    _care_tuple('AppleCare+ for iMac',                'applecare-imac',                'iMac',                9.99,  '3-year'),
    _care_tuple('AppleCare+ for Mac mini',             'applecare-mac-mini',            'Mac mini',            4.49,  '3-year'),
    _care_tuple('AppleCare+ for Mac Studio',           'applecare-mac-studio',          'Mac Studio',         11.49,  '3-year'),
    _care_tuple('AppleCare+ for Mac Pro',              'applecare-mac-pro',             'Mac Pro',            26.99,  '3-year'),
    _care_tuple('AppleCare+ for iPad Pro 11-inch',     'applecare-ipad-pro-11',         'iPad Pro 11-inch',    7.99,  '2-year'),
    _care_tuple('AppleCare+ for iPad Pro 13-inch',     'applecare-ipad-pro-13',         'iPad Pro 13-inch',    8.99,  '2-year'),
    _care_tuple('AppleCare+ for iPad Air',             'applecare-ipad-air',            'iPad Air',            5.99,  '2-year'),
    _care_tuple('AppleCare+ for iPad mini',            'applecare-ipad-mini',           'iPad mini',           5.99,  '2-year'),
    _care_tuple('AppleCare+ for iPad',                 'applecare-ipad',                'iPad',                3.99,  '2-year'),
    _care_tuple('AppleCare+ for Apple Watch Series 11','applecare-watch-series-11',     'Apple Watch Series 11', 3.99,  '2-year'),
    _care_tuple('AppleCare+ for Apple Watch Ultra 3',  'applecare-watch-ultra-3',       'Apple Watch Ultra 3', 4.99,  '2-year'),
    _care_tuple('AppleCare+ for Apple Watch SE',       'applecare-watch-se',            'Apple Watch SE',       2.49,  '2-year'),
    _care_tuple('AppleCare+ for AirPods Pro 3',        'applecare-airpods-pro-3',       'AirPods Pro 3',       1.99,  '2-year'),
    _care_tuple('AppleCare+ for AirPods Max',          'applecare-airpods-max-2',       'AirPods Max',         3.99,  '2-year'),
    _care_tuple('AppleCare+ for AirPods',              'applecare-airpods-4',           'AirPods 4',           1.49,  '2-year'),
    _care_tuple('AppleCare+ for HomePod',              'applecare-homepod',             'HomePod',             1.49,  '2-year'),
    _care_tuple('AppleCare+ for Apple Vision Pro',     'applecare-vision-pro',          'Apple Vision Pro',   29.99,  '2-year',
                desc='AppleCare+ for Apple Vision Pro adds unlimited incidents of accidental damage protection, prioritized expert support, and battery service.'),
    _care_tuple('AppleCare+ for Apple TV',             'applecare-apple-tv',            'Apple TV 4K',         1.49,  '2-year'),

    # ------------------------------------------------------------ Mac peripherals
    ('Magic Mouse - White', 'magic-mouse-white', 'accessories', 'mac-accessory',
     'Magic Mouse with USB-C charging.',
     'Wireless, rechargeable, Multi-Touch surface for swipes and gestures. USB-C charging port on the bottom.',
     99.0, None, ['White'], [], {'connectivity': 'Bluetooth, USB-C', 'compat': 'Mac'}, 2024, ''),
    ('Magic Mouse - Black', 'magic-mouse-black', 'accessories', 'mac-accessory',
     'Magic Mouse in Black with USB-C charging.',
     'Wireless, rechargeable Magic Mouse in Space Black to pair with MacBook Pro Space Black. USB-C charging.',
     129.0, None, ['Black'], [], {'connectivity': 'Bluetooth, USB-C', 'compat': 'Mac'}, 2024, ''),
    ('Magic Trackpad - White', 'magic-trackpad-white', 'accessories', 'mac-accessory',
     'Magic Trackpad with USB-C.',
     'Force Touch, Multi-Touch gestures, all-day battery, USB-C charging. Edge-to-edge glass surface.',
     129.0, None, ['White'], [], {'connectivity': 'Bluetooth, USB-C', 'compat': 'Mac'}, 2024, ''),
    ('Magic Trackpad - Black', 'magic-trackpad-black', 'accessories', 'mac-accessory',
     'Magic Trackpad in Black.',
     'Force Touch, Multi-Touch gestures, USB-C charging in Space Black.',
     149.0, None, ['Black'], [], {'connectivity': 'Bluetooth, USB-C', 'compat': 'Mac'}, 2024, ''),
    ('Magic Keyboard (US English) - White', 'magic-keyboard-mac-white', 'accessories', 'mac-accessory',
     'Magic Keyboard for Mac.',
     'Compact full-size keyboard with USB-C charging cable. Scissor mechanism for crisp typing.',
     99.0, None, ['White'], [], {'connectivity': 'Bluetooth, USB-C', 'compat': 'Mac', 'layout': 'US English'}, 2024, ''),
    ('Magic Keyboard with Touch ID', 'magic-keyboard-touch-id', 'accessories', 'mac-accessory',
     'Magic Keyboard with Touch ID.',
     'Compact full-size keyboard with Touch ID for fast sign-in and Apple Pay. Requires Apple silicon Mac.',
     129.0, None, ['White'], [], {'compat': 'Apple silicon Mac', 'features': 'Touch ID'}, 2024, ''),
    ('Magic Keyboard with Numeric Keypad', 'magic-keyboard-numeric', 'accessories', 'mac-accessory',
     'Full-size keyboard with numeric keypad.',
     'Extended-layout Magic Keyboard with numeric keypad and arrow keys for spreadsheets and data entry.',
     129.0, None, ['White', 'Black'], [], {'compat': 'Mac', 'layout': 'Extended'}, 2024, ''),
    ('Magic Keyboard with Touch ID and Numeric Keypad', 'magic-keyboard-touch-id-numeric', 'accessories', 'mac-accessory',
     'Touch ID + numeric keypad.',
     'Extended Magic Keyboard with Touch ID and numeric keypad. USB-C charging.',
     149.0, None, ['White', 'Black'], [], {'compat': 'Apple silicon Mac', 'layout': 'Extended', 'features': 'Touch ID'}, 2024, ''),
    ('Studio Display - Standard Glass - Tilt-adjustable Stand', 'studio-display-standard-tilt', 'mac', 'display',
     '27-inch 5K Retina display.',
     '27-inch 5K Retina display, 600 nits brightness, P3 wide color, True Tone, 12MP Ultra Wide camera with Center Stage, six-speaker sound system with Spatial Audio.',
     1599.0, 133.25, ['Silver'], [], {'resolution': '5120x2880', 'brightness': '600 nits', 'camera': '12MP Ultra Wide'}, 2024, ''),
    ('Studio Display - Nano-texture Glass - Tilt-adjustable Stand', 'studio-display-nano-tilt', 'mac', 'display',
     'Nano-texture glass for minimal glare.',
     'Studio Display with nano-texture glass to scatter reflections without losing contrast. Perfect for color-critical work.',
     1899.0, 158.25, ['Silver'], [], {'resolution': '5120x2880', 'glass': 'Nano-texture'}, 2024, ''),
    ('Studio Display - Standard Glass - Tilt- and Height-adjustable Stand', 'studio-display-standard-height', 'mac', 'display',
     'Height-adjustable stand.',
     'Studio Display with tilt- and height-adjustable stand for a more ergonomic setup.',
     1999.0, 166.58, ['Silver'], [], {'resolution': '5120x2880', 'stand': 'Tilt and height'}, 2024, ''),
    ('Studio Display - VESA Mount Adapter', 'studio-display-vesa', 'mac', 'display',
     'VESA mount.',
     'Studio Display with VESA mount adapter for wall, articulating-arm, or third-party-stand mounting.',
     1599.0, 133.25, ['Silver'], [], {'resolution': '5120x2880', 'stand': 'VESA'}, 2024, ''),
    ('Pro Display XDR - Standard Glass', 'pro-display-xdr-standard', 'mac', 'display',
     'Pro reference display.',
     'Pro Display XDR with 32-inch 6K Retina display, 1000 nits sustained / 1600 nits peak, P3 wide color, 1000000:1 contrast ratio.',
     4999.0, 416.58, ['Silver'], [], {'resolution': '6016x3384', 'brightness': '1600 nits peak'}, 2024, ''),
    ('Pro Display XDR - Nano-texture Glass', 'pro-display-xdr-nano', 'mac', 'display',
     'Pro reference display with nano-texture.',
     'Pro Display XDR with nano-texture glass for true matte finish on a 6K reference display.',
     5999.0, 499.92, ['Silver'], [], {'resolution': '6016x3384', 'glass': 'Nano-texture'}, 2024, ''),
    ('Pro Stand', 'pro-stand', 'accessories', 'display',
     'For Pro Display XDR.',
     'Tilt, rotate, and height-adjust the Pro Display XDR. Attaches magnetically with no cables.',
     999.0, None, ['Silver'], [], {'compat': 'Pro Display XDR'}, 2019, ''),
    ('VESA Mount Adapter for Pro Display XDR', 'pro-display-xdr-vesa', 'accessories', 'display',
     'VESA mount.',
     'VESA Mount Adapter for Pro Display XDR. 100mm x 100mm.',
     199.0, None, ['Silver'], [], {'compat': 'Pro Display XDR'}, 2019, ''),

    # ------------------------------------------------------------ iPad accessories
    _smart_folio_tuple('Smart Folio for iPad Pro 13-inch (M4) - Black',  'smart-folio-ipad-pro-13-m4-black',  'iPad Pro 13-inch (M4)',  'Black',       99.0, 2024),
    _smart_folio_tuple('Smart Folio for iPad Pro 13-inch (M4) - White',  'smart-folio-ipad-pro-13-m4-white',  'iPad Pro 13-inch (M4)',  'White',       99.0, 2024),
    _smart_folio_tuple('Smart Folio for iPad Pro 13-inch (M4) - Denim',  'smart-folio-ipad-pro-13-m4-denim',  'iPad Pro 13-inch (M4)',  'Denim',       99.0, 2024),
    _smart_folio_tuple('Smart Folio for iPad Pro 11-inch (M4) - Black',  'smart-folio-ipad-pro-11-m4-black',  'iPad Pro 11-inch (M4)',  'Black',       79.0, 2024),
    _smart_folio_tuple('Smart Folio for iPad Pro 11-inch (M4) - White',  'smart-folio-ipad-pro-11-m4-white',  'iPad Pro 11-inch (M4)',  'White',       79.0, 2024),
    _smart_folio_tuple('Smart Folio for iPad Pro 11-inch (M4) - Denim',  'smart-folio-ipad-pro-11-m4-denim',  'iPad Pro 11-inch (M4)',  'Denim',       79.0, 2024),
    _smart_folio_tuple('Smart Folio for iPad Air 13-inch (M4) - Black',  'smart-folio-ipad-air-13-m4-black',  'iPad Air 13-inch (M4)',  'Black',       79.0, 2024),
    _smart_folio_tuple('Smart Folio for iPad Air 13-inch (M4) - Light Violet', 'smart-folio-ipad-air-13-m4-light-violet', 'iPad Air 13-inch (M4)', 'Light Violet', 79.0, 2024),
    _smart_folio_tuple('Smart Folio for iPad Air 11-inch (M4) - Black',  'smart-folio-ipad-air-11-m4-black',  'iPad Air 11-inch (M4)',  'Black',       69.0, 2024),
    _smart_folio_tuple('Smart Folio for iPad Air 11-inch (M4) - Sage',   'smart-folio-ipad-air-11-m4-sage',   'iPad Air 11-inch (M4)',  'Sage',        69.0, 2024),
    _smart_folio_tuple('Smart Folio for iPad Air 11-inch (M4) - Charcoal Gray', 'smart-folio-ipad-air-11-m4-charcoal', 'iPad Air 11-inch (M4)', 'Charcoal Gray', 69.0, 2024),
    _smart_folio_tuple('Smart Folio for iPad (A16) - Black',             'smart-folio-ipad-a16-black',        'iPad (A16)',              'Black',       79.0, 2025),
    _smart_folio_tuple('Smart Folio for iPad (A16) - Light Use',         'smart-folio-ipad-a16-light-use',    'iPad (A16)',              'Light Use',   79.0, 2025),
    _smart_folio_tuple('Smart Folio for iPad mini (A17 Pro) - Dark Cherry', 'smart-folio-ipad-mini-a17-dark-cherry', 'iPad mini (A17 Pro)', 'Dark Cherry', 59.0, 2024),
    _smart_folio_tuple('Smart Folio for iPad mini (A17 Pro) - Sage',     'smart-folio-ipad-mini-a17-sage',    'iPad mini (A17 Pro)',     'Sage',        59.0, 2024),
    _magic_kbd_ipad_tuple('Magic Keyboard for iPad Pro 13-inch (M4) - Black',  'magic-keyboard-ipad-pro-13-m4-black',  'iPad Pro 13-inch (M4)',  'Black',  349.0, 2024),
    _magic_kbd_ipad_tuple('Magic Keyboard for iPad Pro 13-inch (M4) - White',  'magic-keyboard-ipad-pro-13-m4-white',  'iPad Pro 13-inch (M4)',  'White',  349.0, 2024),
    _magic_kbd_ipad_tuple('Magic Keyboard for iPad Pro 11-inch (M4) - Black',  'magic-keyboard-ipad-pro-11-m4-black',  'iPad Pro 11-inch (M4)',  'Black',  299.0, 2024),
    _magic_kbd_ipad_tuple('Magic Keyboard for iPad Pro 11-inch (M4) - White',  'magic-keyboard-ipad-pro-11-m4-white',  'iPad Pro 11-inch (M4)',  'White',  299.0, 2024),
    _magic_kbd_ipad_tuple('Magic Keyboard for iPad Air 13-inch (M4) - Black',  'magic-keyboard-ipad-air-13-m4-black',  'iPad Air 13-inch (M4)',  'Black',  319.0, 2024),
    _magic_kbd_ipad_tuple('Magic Keyboard for iPad Air 11-inch (M4) - Black',  'magic-keyboard-ipad-air-11-m4-black',  'iPad Air 11-inch (M4)',  'Black',  269.0, 2024),
    _magic_kbd_ipad_tuple('Magic Keyboard Folio for iPad (A16) - White',       'magic-keyboard-folio-ipad-a16',         'iPad (A16)',              'White',  249.0, 2025),
    ('Apple Pencil Pro - Tip Refills',         'apple-pencil-pro-tips',     'accessories', 'pencil',
     'Pack of 4 replacement tips.',
     'Spare Apple Pencil Pro tips. Four-pack of replacement tips for Apple Pencil Pro.',
     19.0, None, ['White'], [], {'compat': 'Apple Pencil Pro', 'qty': 4}, 2024, ''),
    ('Apple Pencil (2nd generation) Tips',     'apple-pencil-2-tips',       'accessories', 'pencil',
     'Pack of 4 replacement tips.',
     'Spare tips for Apple Pencil (2nd generation). Four-pack.',
     19.0, None, ['White'], [], {'compat': 'Apple Pencil (2nd generation)', 'qty': 4}, 2024, ''),
    ('USB-C to Apple Pencil Adapter',          'usb-c-apple-pencil-adapter','accessories', 'pencil',
     'Charge and pair via USB-C.',
     'Adapter to charge and pair Apple Pencil (1st generation) with iPad models that have a USB-C port.',
     9.0, None, ['White'], [], {'compat': 'Apple Pencil 1st gen', 'kind': 'adapter'}, 2022, ''),

    # ------------------------------------------------------------ Chargers / cables / adapters
    ('MagSafe Charger (1 m)', 'magsafe-charger-1m', 'accessories', 'charger',
     'Wireless. Smart. Magnetic.',
     'MagSafe Charger with 1 m USB-C cable. Magnetically attaches to iPhone for up to 15W wireless charging with a compatible adapter.',
     39.0, None, ['White'], [], {'length': '1 m', 'power': '15W', 'compat': 'iPhone with MagSafe'}, 2024, ''),
    ('MagSafe Charger (2 m)', 'magsafe-charger-2m', 'accessories', 'charger',
     'MagSafe with a 2 m cable.',
     'MagSafe Charger with 2 m USB-C cable. Convenient for desk and nightstand setups.',
     49.0, None, ['White'], [], {'length': '2 m', 'power': '15W', 'compat': 'iPhone with MagSafe'}, 2024, ''),
    ('MagSafe Duo Charger', 'magsafe-duo-charger', 'accessories', 'charger',
     'Foldable. For iPhone and Apple Watch.',
     'MagSafe Duo Charger folds for travel and charges iPhone and Apple Watch from a single source. Includes USB-C to Lightning cable.',
     129.0, None, ['White'], [], {'compat': 'iPhone, Apple Watch'}, 2024, ''),
    ('20W USB-C Power Adapter', 'usb-c-power-adapter-20w', 'accessories', 'charger',
     '20W fast charging.',
     'Compact, durable 20W USB-C Power Adapter for iPhone, iPad, and AirPods. Fast-charge iPhone 8 and later.',
     19.0, None, ['White'], [], {'power': '20W', 'port': 'USB-C'}, 2024, ''),
    ('30W USB-C Power Adapter', 'usb-c-power-adapter-30w', 'accessories', 'charger',
     '30W fast charging.',
     '30W USB-C Power Adapter for iPad Pro, iPad Air, MacBook Air. Compact design with foldable prongs on some regions.',
     39.0, None, ['White'], [], {'power': '30W', 'port': 'USB-C'}, 2024, ''),
    ('35W Dual USB-C Port Power Adapter', 'usb-c-power-adapter-35w-dual', 'accessories', 'charger',
     'Two USB-C ports.',
     '35W Dual USB-C Port Power Adapter. Charge two devices simultaneously with intelligent power distribution.',
     59.0, None, ['White'], [], {'power': '35W', 'ports': '2x USB-C'}, 2024, ''),
    ('35W Dual USB-C Port Compact Power Adapter', 'usb-c-power-adapter-35w-compact', 'accessories', 'charger',
     'Compact dual USB-C.',
     '35W Dual USB-C Port Compact Power Adapter with foldable prongs. Charge two devices on the go.',
     59.0, None, ['White'], [], {'power': '35W', 'ports': '2x USB-C', 'foldable': True}, 2024, ''),
    ('67W USB-C Power Adapter', 'usb-c-power-adapter-67w', 'accessories', 'charger',
     '67W fast-charge MacBook Air.',
     '67W USB-C Power Adapter for MacBook Air. Supports fast charging on 13-inch and 15-inch models.',
     59.0, None, ['White'], [], {'power': '67W', 'port': 'USB-C'}, 2024, ''),
    ('70W USB-C Power Adapter', 'usb-c-power-adapter-70w', 'accessories', 'charger',
     '70W for MacBook Pro 14".',
     '70W USB-C Power Adapter included with MacBook Pro 14-inch with M4 chip.',
     59.0, None, ['White'], [], {'power': '70W', 'port': 'USB-C'}, 2024, ''),
    ('96W USB-C Power Adapter', 'usb-c-power-adapter-96w', 'accessories', 'charger',
     '96W charger.',
     '96W USB-C Power Adapter for MacBook Pro 14-inch with M4 Pro.',
     79.0, None, ['White'], [], {'power': '96W', 'port': 'USB-C'}, 2024, ''),
    ('140W USB-C Power Adapter', 'usb-c-power-adapter-140w', 'accessories', 'charger',
     '140W for MacBook Pro 16".',
     '140W USB-C Power Adapter for MacBook Pro 16-inch. Supports fast charging via MagSafe 3.',
     99.0, None, ['White'], [], {'power': '140W', 'port': 'USB-C'}, 2024, ''),
    _adapter_tuple('USB-C to MagSafe 3 Cable (2 m)', 'usb-c-to-magsafe-3-2m',     'USB-C', 'MagSafe 3', '2 m', 49.0, 2024),
    _adapter_tuple('USB-C to MagSafe 3 Cable (2 m) - Space Black', 'usb-c-to-magsafe-3-2m-black', 'USB-C', 'MagSafe 3', '2 m', 49.0, 2024),
    _adapter_tuple('USB-C Charge Cable (1 m)',       'usb-c-charge-cable-1m',     'USB-C', 'USB-C',     '1 m', 19.0, 2024),
    _adapter_tuple('USB-C Charge Cable (2 m)',       'usb-c-charge-cable-2m',     'USB-C', 'USB-C',     '2 m', 29.0, 2024),
    _adapter_tuple('USB-C Woven Charge Cable (1 m)', 'usb-c-woven-charge-cable-1m','USB-C', 'USB-C',    '1 m', 19.0, 2025),
    _adapter_tuple('Thunderbolt 4 Pro Cable (1 m)',  'thunderbolt-4-pro-1m',      'Thunderbolt 4', 'Thunderbolt 4', '1 m', 129.0, 2024),
    _adapter_tuple('Thunderbolt 4 Pro Cable (1.8 m)','thunderbolt-4-pro-18m',     'Thunderbolt 4', 'Thunderbolt 4', '1.8 m', 159.0, 2024),
    _adapter_tuple('Thunderbolt 4 Pro Cable (3 m)',  'thunderbolt-4-pro-3m',      'Thunderbolt 4', 'Thunderbolt 4', '3 m', 199.0, 2024),
    _adapter_tuple('Apple USB-C to Lightning Cable (1 m)', 'usb-c-to-lightning-1m','USB-C', 'Lightning', '1 m', 19.0, 2024),
    _adapter_tuple('Apple USB-C to Lightning Cable (2 m)', 'usb-c-to-lightning-2m','USB-C', 'Lightning', '2 m', 29.0, 2024),
    _adapter_tuple('USB-C to 3.5 mm Headphone Jack Adapter','usb-c-headphone-jack','USB-C','3.5 mm Headphone Jack','—', 9.0, 2024),
    _adapter_tuple('Lightning to 3.5 mm Headphone Jack Adapter','lightning-headphone-jack','Lightning','3.5 mm Headphone Jack','—', 9.0, 2024),
    _adapter_tuple('USB-C Digital AV Multiport Adapter','usb-c-digital-av-multiport','USB-C','HDMI + USB-A + USB-C','—', 69.0, 2024),
    _adapter_tuple('USB-C VGA Multiport Adapter',    'usb-c-vga-multiport',       'USB-C', 'VGA + USB-A + USB-C', '—', 69.0, 2024),
    _adapter_tuple('USB-C to USB Adapter',           'usb-c-to-usb-adapter',      'USB-C', 'USB-A',     '—', 19.0, 2024),
    _adapter_tuple('USB-C to SD Card Reader',        'usb-c-sd-card-reader',      'USB-C', 'SD Card',   '—', 39.0, 2024),
    _adapter_tuple('Apple AV Adapter for Apple TV',  'apple-tv-av-adapter',       'USB-C', 'HDMI',      '—', 19.0, 2024),
    ('World Travel Adapter Kit', 'world-travel-adapter-kit', 'accessories', 'charger',
     'Plug adapters for international use.',
     'Includes seven AC plugs that work in North America, Japan, China, the UK, Continental Europe, Korea, Australia, Hong Kong, and Brazil. Compatible with Apple USB-C Power Adapters.',
     29.0, None, ['White'], [], {'plugs': 7}, 2024, ''),

    # ------------------------------------------------------------ EarPods / wired audio
    ('EarPods (USB-C)', 'earpods-usb-c', 'airpods', '',
     'Iconic wired buds with USB-C.',
     'EarPods with USB-C plug. Designed to direct sound into the ear for greater clarity and efficiency.',
     19.0, None, ['White'], [], {'connector': 'USB-C'}, 2024, ''),
    ('EarPods (Lightning)', 'earpods-lightning', 'airpods', '',
     'Iconic wired buds with Lightning.',
     'EarPods with Lightning connector. Bundled with older iPhones.',
     19.0, None, ['White'], [], {'connector': 'Lightning'}, 2024, ''),
    ('EarPods (3.5 mm)', 'earpods-3-5mm', 'airpods', '',
     'Iconic wired buds with 3.5 mm jack.',
     'EarPods with 3.5 mm Headphone Plug. Works with any device that has a 3.5 mm headphone jack.',
     19.0, None, ['White'], [], {'connector': '3.5 mm'}, 2024, ''),

    # ------------------------------------------------------------ Beats expanded
    ('Beats Studio Pro - Black',         'beats-studio-pro-black',         'airpods', '',
     'High-fidelity wireless headphones.',
     'Beats Studio Pro headphones. Personalized Spatial Audio, USB-C lossless audio, ANC, up to 40 hours battery.',
     349.99, 14.58, ['Black'], [], {'anc': True, 'codec': 'AAC, USB-C lossless'}, 2023, ''),
    ('Beats Studio Pro - Sandstone',     'beats-studio-pro-sandstone',     'airpods', '',
     'Beats Studio Pro in Sandstone.',
     'Beats Studio Pro headphones in Sandstone colorway.',
     349.99, 14.58, ['Sandstone'], [], {'anc': True}, 2023, ''),
    ('Beats Studio Pro - Navy',          'beats-studio-pro-navy',          'airpods', '',
     'Beats Studio Pro in Navy.',
     'Beats Studio Pro headphones in Navy colorway.',
     349.99, 14.58, ['Navy'], [], {'anc': True}, 2023, ''),
    ('Beats Studio Buds + - Transparent','beats-studio-buds-plus-transparent','airpods', '',
     'Beats Studio Buds + transparent.',
     'Beats Studio Buds + with transparent shell. Active Noise Cancelling and Apple H1-class platform features.',
     169.99, None, ['Transparent'], [], {'anc': True}, 2023, ''),
    ('Beats Studio Buds + - Black/Gold', 'beats-studio-buds-plus-black-gold','airpods', '',
     'Black/Gold colorway.',
     'Beats Studio Buds + in Black/Gold.',
     169.99, None, ['Black', 'Gold'], [], {'anc': True}, 2023, ''),
    ('Beats Studio Buds + - Ivory',      'beats-studio-buds-plus-ivory',   'airpods', '',
     'Ivory Beats Studio Buds +.',
     'Beats Studio Buds + in Ivory.',
     169.99, None, ['Ivory'], [], {'anc': True}, 2023, ''),
    ('Beats Solo 4 - Matte Black',       'beats-solo-4-matte-black',       'airpods', '',
     'Beats Solo 4 on-ear in Matte Black.',
     'Beats Solo 4 on-ear headphones in Matte Black. 50 hours battery, USB-C charging.',
     199.99, None, ['Matte Black'], [], {'battery': '50 hr'}, 2024, ''),
    ('Beats Solo 4 - Slate Blue',        'beats-solo-4-slate-blue',        'airpods', '',
     'Slate Blue Beats Solo 4.',
     'Beats Solo 4 in Slate Blue.',
     199.99, None, ['Slate Blue'], [], {'battery': '50 hr'}, 2024, ''),
    ('Beats Solo 4 - Cloud Pink',        'beats-solo-4-cloud-pink',        'airpods', '',
     'Cloud Pink Beats Solo 4.',
     'Beats Solo 4 in Cloud Pink.',
     199.99, None, ['Cloud Pink'], [], {'battery': '50 hr'}, 2024, ''),
    ('Beats Pill - Statement Red',       'beats-pill-statement-red',       'audio', '',
     'Bluetooth speaker, 24-hour battery.',
     'Beats Pill portable speaker in Statement Red. 24-hour battery, USB-C charging, IP67 rated.',
     149.99, None, ['Red'], [], {'battery': '24 hr', 'ip': 'IP67'}, 2024, ''),
    ('Beats Pill - Champagne Gold',      'beats-pill-champagne-gold',      'audio', '',
     'Champagne Gold Beats Pill.',
     'Beats Pill portable speaker in Champagne Gold.',
     149.99, None, ['Gold'], [], {'battery': '24 hr', 'ip': 'IP67'}, 2024, ''),
    ('Beats Pill - Matte Black',         'beats-pill-matte-black',         'audio', '',
     'Beats Pill in Matte Black.',
     'Beats Pill portable speaker in Matte Black.',
     149.99, None, ['Matte Black'], [], {'battery': '24 hr', 'ip': 'IP67'}, 2024, ''),

    # ------------------------------------------------------------ iPhone 17 series cases / wallets
    ('iPhone 17 Pro Max Silicone Case with MagSafe - Black',  'iphone-17-pro-max-silicone-black',  'accessories', 'iphone-case', 'Designed by Apple.',
     'Silicone Case for iPhone 17 Pro Max in Black. MagSafe-compatible. Soft microfiber lining.', 49.0, None, ['Black'], [], {'compat': 'iPhone 17 Pro Max', 'kind': 'Silicone Case'}, 2025, ''),
    ('iPhone 17 Pro Max Silicone Case with MagSafe - Cypress','iphone-17-pro-max-silicone-cypress','accessories', 'iphone-case', 'Designed by Apple.',
     'Silicone Case for iPhone 17 Pro Max in Cypress.', 49.0, None, ['Cypress'], [], {'compat': 'iPhone 17 Pro Max', 'kind': 'Silicone Case'}, 2025, ''),
    ('iPhone 17 Pro Max Silicone Case with MagSafe - Plum',   'iphone-17-pro-max-silicone-plum',   'accessories', 'iphone-case', 'Designed by Apple.',
     'Silicone Case for iPhone 17 Pro Max in Plum.', 49.0, None, ['Plum'], [], {'compat': 'iPhone 17 Pro Max', 'kind': 'Silicone Case'}, 2025, ''),
    ('iPhone 17 Pro Max Silicone Case with MagSafe - Natural Tan', 'iphone-17-pro-max-silicone-tan','accessories', 'iphone-case', 'Designed by Apple.',
     'Silicone Case for iPhone 17 Pro Max in Natural Tan.', 49.0, None, ['Natural Tan'], [], {'compat': 'iPhone 17 Pro Max', 'kind': 'Silicone Case'}, 2025, ''),
    ('iPhone 17 Pro Max Silicone Case with MagSafe - Storm Blue','iphone-17-pro-max-silicone-blue','accessories', 'iphone-case', 'Designed by Apple.',
     'Silicone Case for iPhone 17 Pro Max in Storm Blue.', 49.0, None, ['Storm Blue'], [], {'compat': 'iPhone 17 Pro Max', 'kind': 'Silicone Case'}, 2025, ''),
    ('iPhone 17 Pro Max Clear Case with MagSafe', 'iphone-17-pro-max-clear-magsafe', 'accessories', 'iphone-case',
     'Show off the iPhone.', 'Clear Case with MagSafe for iPhone 17 Pro Max. Optical-grade material.', 49.0, None, ['Clear'], [], {'compat': 'iPhone 17 Pro Max', 'kind': 'Clear Case'}, 2025, ''),
    ('iPhone Air Silicone Case with MagSafe - Black',   'iphone-air-silicone-black',  'accessories', 'iphone-case', 'Designed by Apple.', 'Silicone Case for iPhone Air in Black.', 49.0, None, ['Black'], [], {'compat': 'iPhone Air', 'kind': 'Silicone Case'}, 2025, ''),
    ('iPhone Air Silicone Case with MagSafe - Midnight','iphone-air-silicone-midnight','accessories','iphone-case', 'Designed by Apple.', 'Silicone Case for iPhone Air in Midnight.', 49.0, None, ['Midnight'], [], {'compat': 'iPhone Air', 'kind': 'Silicone Case'}, 2025, ''),
    ('iPhone Air Silicone Case with MagSafe - Starlight','iphone-air-silicone-starlight','accessories','iphone-case','Designed by Apple.', 'Silicone Case for iPhone Air in Starlight.', 49.0, None, ['Starlight'], [], {'compat': 'iPhone Air', 'kind': 'Silicone Case'}, 2025, ''),
    ('iPhone Air Silicone Case with MagSafe - Green',   'iphone-air-silicone-green',  'accessories', 'iphone-case', 'Designed by Apple.', 'Silicone Case for iPhone Air in Green.', 49.0, None, ['Green'], [], {'compat': 'iPhone Air', 'kind': 'Silicone Case'}, 2025, ''),
    ('iPhone Air Clear Case with MagSafe',              'iphone-air-clear-magsafe',   'accessories', 'iphone-case', 'Show off the iPhone.', 'Clear Case with MagSafe for iPhone Air.', 49.0, None, ['Clear'], [], {'compat': 'iPhone Air', 'kind': 'Clear Case'}, 2025, ''),
    ('iPhone 17e Silicone Case with MagSafe - Black',   'iphone-17e-silicone-black',  'accessories', 'iphone-case', 'Designed by Apple.', 'Silicone Case for iPhone 17e in Black.', 39.0, None, ['Black'], [], {'compat': 'iPhone 17e', 'kind': 'Silicone Case'}, 2025, ''),
    ('iPhone 17e Silicone Case with MagSafe - Pink',    'iphone-17e-silicone-pink',   'accessories', 'iphone-case', 'Designed by Apple.', 'Silicone Case for iPhone 17e in Light Pink.', 39.0, None, ['Pink'], [], {'compat': 'iPhone 17e', 'kind': 'Silicone Case'}, 2025, ''),
    ('iPhone 17e Silicone Case with MagSafe - Green',   'iphone-17e-silicone-green',  'accessories', 'iphone-case', 'Designed by Apple.', 'Silicone Case for iPhone 17e in Green.', 39.0, None, ['Green'], [], {'compat': 'iPhone 17e', 'kind': 'Silicone Case'}, 2025, ''),
    ('iPhone 17e Clear Case with MagSafe',              'iphone-17e-clear-magsafe',   'accessories', 'iphone-case', 'Show off the iPhone.', 'Clear Case with MagSafe for iPhone 17e.', 39.0, None, ['Clear'], [], {'compat': 'iPhone 17e', 'kind': 'Clear Case'}, 2025, ''),
    ('iPhone FineWoven Wallet with MagSafe - Black',    'iphone-finewoven-wallet-black',   'accessories', 'iphone-case', 'Wallet with MagSafe.', 'FineWoven Wallet with MagSafe in Black. Holds up to 3 cards. Find My support.', 59.0, None, ['Black'], [], {'kind': 'Wallet', 'feature': 'Find My'}, 2024, ''),
    ('iPhone FineWoven Wallet with MagSafe - Mulberry', 'iphone-finewoven-wallet-mulberry','accessories', 'iphone-case', 'Wallet with MagSafe.', 'FineWoven Wallet with MagSafe in Mulberry.', 59.0, None, ['Mulberry'], [], {'kind': 'Wallet', 'feature': 'Find My'}, 2024, ''),
    ('iPhone FineWoven Wallet with MagSafe - Pacific Blue','iphone-finewoven-wallet-pacific','accessories', 'iphone-case', 'Wallet with MagSafe.', 'FineWoven Wallet with MagSafe in Pacific Blue.', 59.0, None, ['Pacific Blue'], [], {'kind': 'Wallet', 'feature': 'Find My'}, 2024, ''),
    ('iPhone FineWoven Wallet with MagSafe - Taupe',    'iphone-finewoven-wallet-taupe',   'accessories', 'iphone-case', 'Wallet with MagSafe.', 'FineWoven Wallet with MagSafe in Taupe.', 59.0, None, ['Taupe'], [], {'kind': 'Wallet', 'feature': 'Find My'}, 2024, ''),
    _crossbody_tuple('Black',         59.0),
    _crossbody_tuple('Stone Gray',    59.0),
    _crossbody_tuple('Pacific Blue',  59.0),
    _crossbody_tuple('Bright Orange', 59.0),
    _crossbody_tuple('Lake Green',    59.0),
    _crossbody_tuple('Mulberry',      59.0),
    _crossbody_tuple('Sun Yellow',    59.0),

    # ------------------------------------------------------------ Watch bands R3 (Trail / Alpine / Ocean / Modern Buckle / Hermès / Nike / Braided Solo)
    _watch_band_tuple('Trail Loop - 49mm Black/Gray',   'trail-loop-49mm-black-gray',  'Black/Gray',  99.0, 2024, 'Apple Watch Ultra'),
    _watch_band_tuple('Trail Loop - 49mm Blue/Black',   'trail-loop-49mm-blue-black',  'Blue/Black',  99.0, 2024, 'Apple Watch Ultra'),
    _watch_band_tuple('Trail Loop - 49mm Green/Gray',   'trail-loop-49mm-green-gray',  'Green/Gray',  99.0, 2024, 'Apple Watch Ultra'),
    _watch_band_tuple('Trail Loop - 49mm Yellow/Beige', 'trail-loop-49mm-yellow-beige','Yellow/Beige',99.0, 2024, 'Apple Watch Ultra'),
    _watch_band_tuple('Alpine Loop - 49mm Black',       'alpine-loop-49mm-black',      'Black',       99.0, 2024, 'Apple Watch Ultra'),
    _watch_band_tuple('Alpine Loop - 49mm Indigo',      'alpine-loop-49mm-indigo',     'Indigo',      99.0, 2024, 'Apple Watch Ultra'),
    _watch_band_tuple('Alpine Loop - 49mm Olive',       'alpine-loop-49mm-olive',      'Olive',       99.0, 2024, 'Apple Watch Ultra'),
    _watch_band_tuple('Ocean Band - 49mm Black',        'ocean-band-49mm-black',       'Black',       99.0, 2024, 'Apple Watch Ultra'),
    _watch_band_tuple('Ocean Band - 49mm White',        'ocean-band-49mm-white',       'White',       99.0, 2024, 'Apple Watch Ultra'),
    _watch_band_tuple('Ocean Band - 49mm Tide Blue',    'ocean-band-49mm-tide-blue',   'Tide Blue',   99.0, 2024, 'Apple Watch Ultra'),
    _watch_band_tuple('Modern Buckle - 41mm Mulberry',  'modern-buckle-41mm-mulberry', 'Mulberry',    149.0, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Modern Buckle - 41mm Black',     'modern-buckle-41mm-black',    'Black',       149.0, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Modern Buckle - 41mm Deep Sea Blue','modern-buckle-41mm-deep-sea','Deep Sea Blue', 149.0, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Braided Solo Loop - 41mm Black', 'braided-solo-41mm-black',     'Black',       99.0, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Braided Solo Loop - 41mm Atlantic Blue','braided-solo-41mm-atlantic','Atlantic Blue',99.0, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Braided Solo Loop - 41mm Plum',  'braided-solo-41mm-plum',      'Plum',        99.0, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Braided Solo Loop - 41mm Storm Blue','braided-solo-41mm-storm','Storm Blue',99.0, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Braided Solo Loop - 45mm Black', 'braided-solo-45mm-black',     'Black',       99.0, 2024, 'Apple Watch 44/45/46mm'),
    _watch_band_tuple('Braided Solo Loop - 45mm Atlantic Blue','braided-solo-45mm-atlantic','Atlantic Blue',99.0, 2024, 'Apple Watch 44/45/46mm'),
    _watch_band_tuple('Braided Solo Loop - 45mm Plum',  'braided-solo-45mm-plum',      'Plum',        99.0, 2024, 'Apple Watch 44/45/46mm'),
    _watch_band_tuple('Nike Sport Band - 41mm Black/Black','nike-sport-41mm-black-black','Black/Black',49.0, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Nike Sport Band - 41mm Pure Platinum/Black','nike-sport-41mm-platinum-black','Pure Platinum/Black',49.0, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Nike Sport Band - 45mm Black/Black','nike-sport-45mm-black-black','Black/Black',49.0, 2024, 'Apple Watch 44/45/46mm'),
    _watch_band_tuple('Nike Sport Loop - 45mm Bright Crimson/Black','nike-sport-loop-45mm-crimson','Bright Crimson/Black',49.0, 2024, 'Apple Watch 44/45/46mm'),
    _watch_band_tuple('Hermès Kilim Single Tour - 41mm Noir/Étoupe','hermes-kilim-41mm-noir-etoupe','Noir/Étoupe',389.0, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Hermès Bridon Single Tour - 45mm Noir','hermes-bridon-45mm-noir','Noir',389.0, 2024, 'Apple Watch 44/45/46mm'),
    _watch_band_tuple('Hermès Toile H Single Tour - 41mm Beton/Sienne','hermes-toile-h-41mm-beton-sienne','Beton/Sienne',439.0, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Hermès Twill Jump Single Tour - 41mm Orange','hermes-twill-41mm-orange','Orange',389.0, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Hermès Casaque Single Tour - 41mm Sesame/Orange','hermes-casaque-41mm-sesame','Sesame/Orange',389.0, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Solo Loop - 41mm Light Pink',   'solo-loop-41mm-light-pink',   'Light Pink',  49.0, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Solo Loop - 41mm Black',        'solo-loop-41mm-black',        'Black',       49.0, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Solo Loop - 45mm Black',        'solo-loop-45mm-black',        'Black',       49.0, 2024, 'Apple Watch 44/45/46mm'),
    _watch_band_tuple('Sport Loop - 41mm Plasma',      'sport-loop-41mm-plasma',      'Plasma',      49.0, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Sport Loop - 45mm Storm Blue',  'sport-loop-45mm-storm-blue',  'Storm Blue',  49.0, 2024, 'Apple Watch 44/45/46mm'),
    _watch_band_tuple('Sport Loop - 45mm Plum',        'sport-loop-45mm-plum',        'Plum',        49.0, 2024, 'Apple Watch 44/45/46mm'),
    _watch_band_tuple('Milanese Loop - 41mm Silver',   'milanese-41mm-silver',        'Silver',      99.0, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Milanese Loop - 41mm Graphite', 'milanese-41mm-graphite',      'Graphite',    99.0, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Milanese Loop - 45mm Silver',   'milanese-45mm-silver',        'Silver',      99.0, 2024, 'Apple Watch 44/45/46mm'),
    _watch_band_tuple('Milanese Loop - 45mm Gold',     'milanese-45mm-gold',          'Gold',        99.0, 2024, 'Apple Watch 44/45/46mm'),
    _watch_band_tuple('Link Bracelet - 41mm Silver',   'link-bracelet-41mm-silver',   'Silver',      349.0, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Link Bracelet - 41mm Space Black','link-bracelet-41mm-space-black','Space Black',349.0, 2024, 'Apple Watch 40/41mm'),
    _watch_band_tuple('Link Bracelet - 45mm Silver',   'link-bracelet-45mm-silver',   'Silver',      349.0, 2024, 'Apple Watch 44/45/46mm'),
    _watch_band_tuple('Sport Band - 45mm Lake Green',  'sport-band-45mm-lake-green',  'Lake Green',  49.0, 2025, 'Apple Watch 44/45/46mm'),
    _watch_band_tuple('Sport Band - 45mm Sun Yellow',  'sport-band-45mm-sun-yellow',  'Sun Yellow',  49.0, 2025, 'Apple Watch 44/45/46mm'),
    _watch_band_tuple('Sport Band - 45mm Bright Orange','sport-band-45mm-bright-orange','Bright Orange',49.0, 2025, 'Apple Watch 44/45/46mm'),

    # ------------------------------------------------------------ HomeKit accessories
    _homekit_tuple('Eve Energy - Smart Plug',          'eve-energy-smart-plug',         'Eve',          'Smart plug',        39.95, 2024, 'Eve Energy with Thread and Matter support. Monitor power consumption, schedule appliances, control with Siri.'),
    _homekit_tuple('Eve Motion - Wireless Sensor',     'eve-motion-sensor',             'Eve',          'Motion sensor',     49.95, 2024, 'Eve Motion. Battery-powered motion sensor with Thread and HomeKit.'),
    _homekit_tuple('Eve Door & Window Sensor',         'eve-door-window-sensor',        'Eve',          'Contact sensor',    39.95, 2024, 'Eve Door & Window. Battery-powered contact sensor with Thread.'),
    _homekit_tuple('Eve Weather - Outdoor Sensor',     'eve-weather-sensor',            'Eve',          'Weather sensor',    79.95, 2024, 'Eve Weather. Outdoor weather station with temperature, humidity, and air pressure.'),
    _homekit_tuple('Aqara M2 Hub',                     'aqara-m2-hub',                  'Aqara',        'Smart home hub',    69.99, 2024, 'Aqara M2 Hub. Zigbee 3.0 hub with HomeKit, Alexa, and Google Home support.'),
    _homekit_tuple('Logitech Circle View Camera',      'logitech-circle-view-camera',   'Logitech',     'Indoor camera',    159.99, 2024, 'Logitech Circle View Indoor wired camera with HomeKit Secure Video.'),
    _homekit_tuple('Logitech Circle View Doorbell',    'logitech-circle-view-doorbell', 'Logitech',     'Doorbell',         199.99, 2024, 'Logitech Circle View wired doorbell with HomeKit Secure Video and face recognition.'),
    _homekit_tuple('Nanoleaf Shapes Hexagons Smarter Kit', 'nanoleaf-shapes-hexagons',  'Nanoleaf',     'Smart lighting',   199.99, 2024, 'Nanoleaf Shapes Hexagons. 9-pack modular smart light panels with Thread border router.'),
    _homekit_tuple('Nanoleaf Lines Smarter Kit',       'nanoleaf-lines-smarter-kit',    'Nanoleaf',     'Smart lighting',   199.99, 2024, 'Nanoleaf Lines. Modular linear smart lights with Thread border router.'),
    _homekit_tuple('Philips Hue White and Color Starter Kit', 'philips-hue-color-starter','Philips Hue','Smart lighting',  199.99, 2024, 'Philips Hue starter kit with Hue Bridge and 3 White and Color Ambiance bulbs.'),
    _homekit_tuple('Yale Assure Lock 2 with HomeKit',  'yale-assure-lock-2-homekit',    'Yale',         'Smart lock',       279.99, 2024, 'Yale Assure Lock 2 touchscreen smart lock with HomeKit support.'),
    _homekit_tuple('Schlage Encode Plus Smart Deadbolt','schlage-encode-plus',          'Schlage',      'Smart lock',       329.99, 2024, 'Schlage Encode Plus WiFi Deadbolt with built-in WiFi and Apple home key (NFC).'),
    _homekit_tuple('Aqara Door & Window Sensor P2',    'aqara-door-window-p2',          'Aqara',        'Contact sensor',    19.99, 2024, 'Aqara P2 Door & Window Sensor with Thread and Matter.'),
    _homekit_tuple('Meross Smart WiFi Garage Door Opener','meross-garage-door',         'Meross',       'Garage opener',     59.99, 2024, 'Meross WiFi Garage Door Opener with HomeKit.'),
    _homekit_tuple('Aqara G3 Hub Camera',              'aqara-g3-camera',               'Aqara',        'Indoor camera',    109.99, 2024, 'Aqara Camera Hub G3 with HomeKit Secure Video and Zigbee/Matter hub.'),
    _homekit_tuple('Onvis Smart Plug B1 with Energy',  'onvis-smart-plug-b1',           'Onvis',        'Smart plug',        29.99, 2024, 'Onvis B1 smart plug with energy monitoring and HomeKit.'),
    _homekit_tuple('Tapo C100 HomeKit Camera',         'tapo-c100-homekit',             'Tapo',         'Indoor camera',     34.99, 2024, 'Tapo C100 Indoor WiFi Camera with HomeKit Secure Video.'),
    _homekit_tuple('VOCOlinc Smart LED Bulb',          'vocolinc-smart-bulb',           'VOCOlinc',     'Smart bulb',        24.99, 2024, 'VOCOlinc White and Color smart LED A19 bulb with HomeKit.'),
    _homekit_tuple('Wemo Stage Scene Controller',      'wemo-stage-scene-controller',   'Belkin Wemo',  'Scene controller',  49.95, 2024, 'Wemo Stage 3-button scene controller with Thread.'),
    _homekit_tuple('LG OLED evo G4 65-inch with AirPlay 2','lg-oled-g4-65',             'LG',           'OLED TV',          2999.99, 2024, 'LG OLED evo G4 65-inch with AirPlay 2 and HomeKit. Brilliance Booster Max.'),

    # ------------------------------------------------------------ Vision Pro accessories R3
    ('Apple Vision Pro Travel Case', 'vision-pro-travel-case', 'accessories', 'vision-pro-accessory',
     'Designed for travel.',
     'Apple Vision Pro Travel Case. Protects the headset, Light Seal, and Battery in transit.',
     199.0, None, ['Charcoal'], [], {'compat': 'Apple Vision Pro'}, 2024, ''),
    ('Apple Vision Pro Battery', 'vision-pro-battery-2', 'accessories', 'vision-pro-accessory',
     'Spare external battery.',
     'External battery for Apple Vision Pro. Up to 2 hours general use, 2.5 hours video playback. Plug into a power outlet for all-day use.',
     199.0, None, ['Silver'], [], {'compat': 'Apple Vision Pro', 'runtime': '2 hr'}, 2024, ''),
    ('Apple Vision Pro Solo Knit Band - Replacement', 'vision-pro-solo-knit-replacement', 'accessories', 'vision-pro-accessory',
     'Replacement Solo Knit Band.',
     'Replacement Solo Knit Band for Apple Vision Pro. Three sizes available.',
     99.0, None, ['Gray'], [], {'compat': 'Apple Vision Pro'}, 2024, ''),
    ('Apple Vision Pro Dual Loop Band - Replacement',  'vision-pro-dual-loop-replacement', 'accessories', 'vision-pro-accessory',
     'Replacement Dual Loop Band.',
     'Replacement Dual Loop Band for Apple Vision Pro.',
     99.0, None, ['Gray'], [], {'compat': 'Apple Vision Pro'}, 2024, ''),
    ('Apple Vision Pro Polishing Cloth', 'vision-pro-polishing-cloth-2', 'accessories', 'vision-pro-accessory',
     'Spare polishing cloth.',
     'Replacement polishing cloth for Apple Vision Pro. Soft, non-abrasive material.',
     19.0, None, ['White'], [], {'compat': 'Apple Vision Pro'}, 2024, ''),
    ('Apple Vision Pro Cover', 'vision-pro-cover-bench', 'accessories', 'vision-pro-accessory',
     'Magnetic display cover.',
     'Magnetic display cover for Apple Vision Pro.',
     19.0, None, ['Charcoal'], [], {'compat': 'Apple Vision Pro'}, 2024, ''),

    # ------------------------------------------------------------ Mac / iPad refurb-style alt SKUs & extras
    ('Apple Studio Display Pivoting Stand Add-on', 'studio-display-pivot-stand-addon', 'accessories', 'display',
     'Add-on accessory.',
     'Studio Display VESA mount accessory for pivoting stand setups.',
     99.0, None, ['Silver'], [], {'compat': 'Studio Display'}, 2024, ''),
    ('Logitech MX Master 3S for Mac', 'logitech-mx-master-3s-mac', 'accessories', 'mac-accessory',
     'Performance wireless mouse.',
     'Logitech MX Master 3S for Mac. Quiet clicks, 8000 DPI, USB-C charging, Flow software support.',
     99.99, None, ['Pale Gray', 'Space Gray'], [], {'compat': 'Mac', 'connectivity': 'Bluetooth, USB-C'}, 2024, ''),
    ('Logitech MX Keys S for Mac', 'logitech-mx-keys-s-mac', 'accessories', 'mac-accessory',
     'Wireless keyboard.',
     'Logitech MX Keys S for Mac. Backlit, USB-C charging, smart illumination.',
     119.99, None, ['Pale Gray', 'Space Gray'], [], {'compat': 'Mac'}, 2024, ''),
    ('Belkin BoostCharge Pro 2-in-1 Wireless Charger', 'belkin-boostcharge-pro-2in1', 'accessories', 'charger',
     '2-in-1 MagSafe + Apple Watch.',
     'Belkin BoostCharge Pro 2-in-1 Wireless Charging Pad. 15W MagSafe + fast-charging Apple Watch.',
     129.99, None, ['White', 'Black'], [], {'power': '15W', 'compat': 'iPhone with MagSafe, Apple Watch'}, 2024, ''),
    ('Belkin BoostCharge Pro 3-in-1 with MagSafe', 'belkin-boostcharge-pro-3in1', 'accessories', 'charger',
     '3-in-1 MagSafe.',
     'Belkin BoostCharge Pro 3-in-1 with MagSafe. Charges iPhone, Apple Watch, and AirPods simultaneously.',
     149.99, None, ['White', 'Black'], [], {'power': '15W', 'compat': 'iPhone, Apple Watch, AirPods'}, 2024, ''),
    ('Mophie 3-in-1 Travel Charger with MagSafe', 'mophie-3in1-travel-magsafe', 'accessories', 'charger',
     'Foldable 3-in-1 travel charger.',
     'Mophie 3-in-1 Travel Charger with MagSafe. Foldable for travel; charges iPhone, Apple Watch, and AirPods.',
     149.95, None, ['Black'], [], {'compat': 'iPhone, Apple Watch, AirPods', 'foldable': True}, 2024, ''),
    ('Anker MagGo Wireless Charging Station 3-in-1', 'anker-maggo-3in1', 'accessories', 'charger',
     'Anker MagGo Qi2 3-in-1.',
     'Anker MagGo Qi2 15W 3-in-1 wireless charging station.',
     149.99, None, ['White'], [], {'power': '15W Qi2'}, 2024, ''),
    ('Twelve South ButterFly 2-in-1 MagSafe Charger', 'twelve-south-butterfly-magsafe', 'accessories', 'charger',
     'Foldable MagSafe charger.',
     'Twelve South ButterFly foldable 2-in-1 MagSafe charger.',
     129.95, None, ['White'], [], {'compat': 'iPhone, Apple Watch'}, 2024, ''),
    ('Native Union Belt Cable Pro USB-C', 'native-union-belt-cable-pro', 'accessories', 'cable',
     'Braided USB-C cable.',
     'Native Union Belt Cable Pro USB-C 240W braided cable, 2.4 m.',
     34.99, None, ['Zebra', 'Black'], [], {'length': '2.4 m', 'power': '240W'}, 2024, ''),
    ('Native Union Drop XL Wireless Charger', 'native-union-drop-xl', 'accessories', 'charger',
     'Wireless charging pad.',
     'Native Union Drop XL Wireless Charger pad in fabric finish.',
     49.99, None, ['Slate', 'Sand'], [], {'power': '10W Qi'}, 2024, ''),

    # ------------------------------------------------------------ Photography / Pro accessories
    ('Apple Polishing Cloth', 'apple-polishing-cloth', 'accessories', 'care',
     'Soft, non-abrasive cloth.',
     'Apple Polishing Cloth. Made with soft, nonabrasive material for cleaning any Apple display.',
     19.0, None, ['White'], [], {'compat': 'Apple displays'}, 2021, ''),
    ('Apple Watch Magnetic Fast Charger to USB-C Cable (1 m)', 'watch-fast-charger-usb-c-1m', 'accessories', 'charger',
     'Fast-charges Apple Watch.',
     'Apple Watch Magnetic Fast Charger to USB-C Cable (1 m). Fast-charges compatible Apple Watch models.',
     29.0, None, ['White'], [], {'length': '1 m', 'compat': 'Apple Watch'}, 2024, ''),
    ('Apple Watch Magnetic Fast Charger to USB-C Cable (2 m)', 'watch-fast-charger-usb-c-2m', 'accessories', 'charger',
     'Fast-charges Apple Watch.',
     'Apple Watch Magnetic Fast Charger to USB-C Cable (2 m).',
     35.0, None, ['White'], [], {'length': '2 m', 'compat': 'Apple Watch'}, 2024, ''),
    ('Apple Watch Magnetic Charging Dock', 'watch-magnetic-charging-dock', 'accessories', 'charger',
     'Apple Watch nightstand dock.',
     'Apple Watch Magnetic Charging Dock. Sits flat for nightstand mode or upright.',
     79.0, None, ['White'], [], {'compat': 'Apple Watch'}, 2024, ''),

    # ------------------------------------------------------------ Apple TV remote / extras
    ('Siri Remote (3rd generation)', 'siri-remote-3rd-gen', 'accessories', 'tv-accessory',
     'Backlit clickpad. USB-C charging.',
     'Siri Remote with Touch-enabled clickpad, dedicated power button, and USB-C charging.',
     59.0, None, ['Silver'], [], {'compat': 'Apple TV'}, 2024, ''),
    ('Apple Remote Loop',         'apple-remote-loop',         'accessories', 'tv-accessory',
     'Wrist loop for Apple TV remote.',
     'Apple Remote Loop. Keeps Siri Remote secure on your wrist.',
     12.95, None, ['Black'], [], {'compat': 'Siri Remote'}, 2024, ''),
    ('Apple TV Ethernet Cable',   'apple-tv-ethernet-cable',   'accessories', 'tv-accessory',
     'Gigabit Ethernet.',
     'Gigabit Ethernet cable for Apple TV 4K.',
     19.0, None, ['Black'], [], {'compat': 'Apple TV 4K'}, 2024, ''),

    # ------------------------------------------------------------ Education bundles / gift cards (recorded as catalog rows)
    ('Apple Gift Card $25',  'apple-gift-card-25',  'accessories', 'service',
     'Apple Gift Card.',
     'Apple Gift Card redeemable for Apple products, accessories, App Store, music, movies, TV shows, iCloud+, and more.',
     25.0,  None, ['Digital'], [], {'denomination': 25,  'kind': 'gift_card'}, 2024, ''),
    ('Apple Gift Card $50',  'apple-gift-card-50',  'accessories', 'service',
     'Apple Gift Card.', 'Apple Gift Card. Redeemable across Apple Store and services.',
     50.0,  None, ['Digital'], [], {'denomination': 50,  'kind': 'gift_card'}, 2024, ''),
    ('Apple Gift Card $100', 'apple-gift-card-100', 'accessories', 'service',
     'Apple Gift Card.', 'Apple Gift Card. Redeemable across Apple Store and services.',
     100.0, None, ['Digital'], [], {'denomination': 100, 'kind': 'gift_card'}, 2024, ''),
    ('Apple Gift Card $200', 'apple-gift-card-200', 'accessories', 'service',
     'Apple Gift Card.', 'Apple Gift Card. Redeemable across Apple Store and services.',
     200.0, None, ['Digital'], [], {'denomination': 200, 'kind': 'gift_card'}, 2024, ''),
    ('Apple Gift Card $500', 'apple-gift-card-500', 'accessories', 'service',
     'Apple Gift Card.', 'Apple Gift Card. Redeemable across Apple Store and services.',
     500.0, None, ['Digital'], [], {'denomination': 500, 'kind': 'gift_card'}, 2024, ''),
]


# Programmatic tail: deterministic additional SKUs to push past 600 products.
# Each item is hand-anchored to a real Apple SKU family.

def _extend_r3():
    extra = []
    # AirTag multi-packs + accessories
    extra.append(('AirTag 4 Pack', 'airtag-4-pack', 'accessories', 'airtag',
                  'Pack of 4 AirTags.',
                  'Four-pack of AirTag for tracking items with Precision Finding via Ultra Wideband.',
                  99.0, None, ['Silver'], [],
                  {'qty': 4, 'features': 'Precision Finding, U1 chip'}, 2024, ''))
    for name, slug, brand, price in [
        ('AirTag Leather Key Ring - Black',          'airtag-leather-keyring-black',          'Apple',  39.0),
        ('AirTag Leather Key Ring - Saddle Brown',   'airtag-leather-keyring-saddle',         'Apple',  39.0),
        ('AirTag Leather Loop - Midnight',           'airtag-leather-loop-midnight',          'Apple',  39.0),
        ('AirTag Leather Loop - Saddle Brown',       'airtag-leather-loop-saddle',            'Apple',  39.0),
        ('AirTag Hermès Travel Tag',                 'airtag-hermes-travel-tag',              'Hermès', 449.0),
        ('AirTag Hermès Bag Charm',                  'airtag-hermes-bag-charm',               'Hermès', 349.0),
        ('AirTag Hermès Luggage Tag',                'airtag-hermes-luggage-tag',             'Hermès', 359.0),
        ('AirTag Hermès Key Ring',                   'airtag-hermes-key-ring',                'Hermès', 349.0),
        ('Belkin Secure Holder for AirTag',          'belkin-secure-holder-airtag',           'Belkin', 12.95),
        ('Belkin Secure Holder with Strap for AirTag','belkin-secure-holder-strap-airtag',    'Belkin', 14.95),
    ]:
        extra.append((name, slug, 'accessories', 'airtag', f'{brand} accessory for AirTag.',
                      f'{name}. Premium accessory for AirTag.', price, None,
                      [brand], [], {'compat': 'AirTag', 'brand': brand}, 2024, ''))

    # More Sport Bands and Loops covering rainbow color matrix per 41/45 mm
    for size, compat in (('41mm', 'Apple Watch 40/41mm'), ('45mm', 'Apple Watch 44/45/46mm')):
        for color in ['Storm Blue', 'Plum', 'Cypress', 'Light Pink', 'Natural Tan',
                      'Lake Green', 'Sun Yellow', 'Bright Orange', 'Stone Gray', 'Pacific Blue']:
            slug = f'sport-band-{size}-{color.lower().replace(" ", "-")}'
            # avoid double-add of any existing R2/R3 slugs
            name = f'Sport Band - {size} {color}'
            extra.append(_watch_band_tuple(name, slug, color, 49.0, 2025, compat))

    # Sport Loops (woven)
    for size, compat in (('41mm', 'Apple Watch 40/41mm'), ('45mm', 'Apple Watch 44/45/46mm')):
        for color in ['Midnight', 'Starlight', 'Pacific Blue', 'Storm Blue', 'Sun Yellow', 'Plum']:
            slug = f'sport-loop-{size}-r3-{color.lower().replace(" ", "-")}'
            name = f'Sport Loop - {size} {color}'
            extra.append(_watch_band_tuple(name, slug, color, 49.0, 2025, compat))

    # Solo Loop additional colors
    for size, compat in (('41mm', 'Apple Watch 40/41mm'), ('45mm', 'Apple Watch 44/45/46mm')):
        for color in ['Storm Blue', 'Plum', 'Sun Yellow', 'Bright Orange', 'Lake Green']:
            slug = f'solo-loop-{size}-r3-{color.lower().replace(" ", "-")}'
            name = f'Solo Loop - {size} {color}'
            extra.append(_watch_band_tuple(name, slug, color, 49.0, 2025, compat))

    # Clear / silicone cases for iPhone 16 / 15 series (legacy support)
    for model, model_slug, colors, price in [
        ('iPhone 16 Pro Max',  'iphone-16-pro-max',  ['Black','Cypress','Plum','Natural Tan','Storm Blue'], 49.0),
        ('iPhone 16 Pro',      'iphone-16-pro',      ['Black','Cypress','Plum','Natural Tan','Storm Blue'], 49.0),
        ('iPhone 16 Plus',     'iphone-16-plus',     ['Black','Lake Green','Pink','Storm Blue'],            49.0),
        ('iPhone 16',          'iphone-16',          ['Black','Lake Green','Pink','Storm Blue'],            49.0),
        ('iPhone 15 Pro Max',  'iphone-15-pro-max',  ['Black','Cypress','Storm Blue'],                      49.0),
        ('iPhone 15',          'iphone-15',          ['Black','Pink','Storm Blue'],                         49.0),
    ]:
        for c in colors:
            extra.append(_case_tuple(
                f'{model} Silicone Case with MagSafe - {c}',
                f'{model_slug}-silicone-magsafe-{c.lower().replace(" ", "-")}',
                model, c, price))
        extra.append(('Clear Case with MagSafe for ' + model,
                      f'{model_slug}-clear-magsafe-r3', 'accessories', 'iphone-case',
                      'Clear Case with MagSafe.',
                      f'Clear Case with MagSafe for {model}.', 49.0, None, ['Clear'], [],
                      {'compat': model, 'kind': 'Clear Case'}, 2024, ''))

    # MagSafe wallets in additional colors
    for c in ['Light Pink', 'Evergreen', 'Wisteria', 'Storm Blue']:
        extra.append(('iPhone FineWoven Wallet with MagSafe - ' + c,
                      f'iphone-finewoven-wallet-{c.lower().replace(" ", "-")}',
                      'accessories', 'iphone-case', 'Wallet with MagSafe.',
                      f'FineWoven Wallet with MagSafe in {c}.', 59.0, None, [c], [],
                      {'kind': 'Wallet', 'feature': 'Find My'}, 2024, ''))

    return extra


EXTRA_PRODUCTS_R3_TAIL = _extend_r3()
EXTRA_PRODUCTS_R3 = EXTRA_PRODUCTS_R3 + EXTRA_PRODUCTS_R3_TAIL


# ---------------------------------------------------------------------------
# R4 product extension (target 605 → 900+).
# All entries are deterministic and synthesized via small builders that mirror
# Apple's real SKU shapes: certified-refurbished tier, education-bundle pricing,
# extended Watch band rainbow, iPhone 17 / 16 / Air case + folio matrix, more
# chargers and USB-C cables, business volume bundles. No DB-table changes.
# ---------------------------------------------------------------------------

def _refurb_tuple(base_name, slug, cat, price_orig, year, chip, colors, storage, specs):
    """Apple Certified Refurbished: typical Apple Store discount is 15% off."""
    refurb_price = round(price_orig * 0.85 / 5) * 5 + 4  # $X9 ladder
    name = f'{base_name} — Certified Refurbished'
    return (name, f'certified-refurbished-{slug}', cat, 'refurbished',
            'Apple Certified Refurbished. One-year warranty.',
            f'{base_name} backed by Apple — fully tested, repackaged, and covered by a one-year Apple limited warranty. '
            f'AppleCare+ available. Free shipping and 14-day returns.',
            float(refurb_price), None, colors, storage,
            dict(specs, refurbished='Certified', warranty='1-year Apple limited'),
            year, chip)


def _edu_bundle_tuple(name, slug, price, mp, colors, storage, specs, year):
    """Education savings SKU. Mirrors Apple's UNiDAYS-verified pricing.

    Education pricing typically saves $50–$200 off Mac/iPad list. We encode
    that explicitly into the SKU so tasks can ask 'what is the education
    price for MacBook Air' and the agent has a single SKU to point at.

    Returns the standard 13-tuple expected by `_seed_extra_products`; the
    monthly-installment column is derived from `mp` in the loader.
    """
    return (name, f'education-savings-{slug}', 'mac', 'education',
            'Save with Apple Education Pricing — UNiDAYS verified.',
            f'{name}. College students, parents buying for college students, and teachers save with Apple Education Pricing. '
            f'Verify your status using UNiDAYS at checkout. Bundles include AirPods on us with an eligible Mac or iPad.',
            float(price), mp, colors, storage, specs, year, '')


def _band_matrix(material, sizes, colors, price, year=2025):
    """Generate (size × color) Watch band SKUs in deterministic order."""
    out = []
    for size, compat in sizes:
        for color in colors:
            slug = f'{material.lower().replace(" ", "-")}-{size}-r4-{color.lower().replace(" ", "-").replace("/", "-")}'
            name = f'{material} - {size} {color}'
            out.append(_watch_band_tuple(name, slug, color, price, year, compat))
    return out


def _extend_r4():
    """R4 expansion — pushes product count from 605 to 900+ with high-quality
    SKUs that mirror real Apple Store inventory categories (refurbished,
    education, today-at-apple-themed accessories, business bundles)."""
    extra = []

    # ------------------------------------------------------------------
    # A. Certified Refurbished tier — popular flagship + recent generation
    # ------------------------------------------------------------------
    refurb_specs_iphone = {'chip': 'A18', 'display': '6.1" Super Retina XDR',
                           'camera': '48MP Main', 'battery': 'Apple-tested'}
    refurb_specs_mac = {'memory': '16GB', 'battery': 'Apple-tested', 'condition': 'A-grade'}
    refurb_specs_ipad = {'display': 'Liquid Retina', 'battery': 'Apple-tested'}
    refurb_specs_watch = {'health': 'Blood oxygen, ECG', 'condition': 'A-grade'}

    for base, slug, price, year, chip in [
        # iPhone refurbished
        ('iPhone 16 Pro Max',    'iphone-16-pro-max',    1199.00, 2024, 'A18 Pro'),
        ('iPhone 16 Pro',        'iphone-16-pro',         999.00, 2024, 'A18 Pro'),
        ('iPhone 16 Plus',       'iphone-16-plus',        899.00, 2024, 'A18'),
        ('iPhone 16',            'iphone-16',             799.00, 2024, 'A18'),
        ('iPhone 15 Pro Max',    'iphone-15-pro-max',    1199.00, 2023, 'A17 Pro'),
        ('iPhone 15 Pro',        'iphone-15-pro',         999.00, 2023, 'A17 Pro'),
        ('iPhone 15 Plus',       'iphone-15-plus',        899.00, 2023, 'A16'),
        ('iPhone 15',            'iphone-15',             799.00, 2023, 'A16'),
        ('iPhone 14 Pro Max',    'iphone-14-pro-max',    1099.00, 2022, 'A16'),
        ('iPhone 14 Pro',        'iphone-14-pro',         999.00, 2022, 'A16'),
        ('iPhone 14 Plus',       'iphone-14-plus',        799.00, 2022, 'A15'),
        ('iPhone 14',            'iphone-14',             699.00, 2022, 'A15'),
        ('iPhone 13 Pro Max',    'iphone-13-pro-max',    1099.00, 2021, 'A15'),
        ('iPhone 13 Pro',        'iphone-13-pro',         999.00, 2021, 'A15'),
        ('iPhone 13',            'iphone-13',             699.00, 2021, 'A15'),
        ('iPhone SE (3rd gen)',  'iphone-se-3',           429.00, 2022, 'A15'),
    ]:
        extra.append(_refurb_tuple(base, slug, 'iphone', price, year, chip,
                                   ['Black', 'White', 'Blue'], ['128GB', '256GB', '512GB'],
                                   refurb_specs_iphone))

    for base, slug, price, year, chip in [
        ('MacBook Pro 14" M4',       'macbook-pro-14-m4',       1599.00, 2024, 'M4'),
        ('MacBook Pro 14" M4 Pro',   'macbook-pro-14-m4-pro',   1999.00, 2024, 'M4 Pro'),
        ('MacBook Pro 16" M4 Pro',   'macbook-pro-16-m4-pro',   2499.00, 2024, 'M4 Pro'),
        ('MacBook Pro 16" M4 Max',   'macbook-pro-16-m4-max',   3499.00, 2024, 'M4 Max'),
        ('MacBook Pro 14" M3',       'macbook-pro-14-m3',       1599.00, 2023, 'M3'),
        ('MacBook Pro 16" M3',       'macbook-pro-16-m3',       2499.00, 2023, 'M3 Pro'),
        ('MacBook Air 13" M3',       'macbook-air-13-m3',       1099.00, 2024, 'M3'),
        ('MacBook Air 15" M3',       'macbook-air-15-m3',       1299.00, 2024, 'M3'),
        ('MacBook Air 13" M2',       'macbook-air-13-m2',        999.00, 2022, 'M2'),
        ('iMac 24" M4',              'imac-24-m4',              1299.00, 2024, 'M4'),
        ('iMac 24" M3',              'imac-24-m3',              1299.00, 2023, 'M3'),
        ('Mac mini M4',              'mac-mini-m4',              599.00, 2024, 'M4'),
        ('Mac mini M4 Pro',          'mac-mini-m4-pro',         1399.00, 2024, 'M4 Pro'),
        ('Mac Studio M2 Max',        'mac-studio-m2-max',       1999.00, 2023, 'M2 Max'),
        ('Mac Studio M2 Ultra',      'mac-studio-m2-ultra',     3999.00, 2023, 'M2 Ultra'),
    ]:
        extra.append(_refurb_tuple(base, slug, 'mac', price, year, chip,
                                   ['Space Black', 'Silver', 'Space Gray'],
                                   ['256GB', '512GB', '1TB', '2TB'],
                                   refurb_specs_mac))

    for base, slug, price, year, chip in [
        ('iPad Pro 11" M4',     'ipad-pro-11-m4',        999.00, 2024, 'M4'),
        ('iPad Pro 13" M4',     'ipad-pro-13-m4',       1299.00, 2024, 'M4'),
        ('iPad Air 11" M4',     'ipad-air-11-m4',        599.00, 2024, 'M4'),
        ('iPad Air 13" M4',     'ipad-air-13-m4',        799.00, 2024, 'M4'),
        ('iPad (10th gen)',     'ipad-10',               349.00, 2022, 'A14 Bionic'),
        ('iPad mini (7th gen)', 'ipad-mini-7',           499.00, 2024, 'A17 Pro'),
        ('iPad Pro 11" M2',     'ipad-pro-11-m2',        799.00, 2022, 'M2'),
    ]:
        extra.append(_refurb_tuple(base, slug, 'ipad', price, year, chip,
                                   ['Space Black', 'Silver', 'Blue', 'Purple'],
                                   ['64GB', '128GB', '256GB', '512GB'],
                                   refurb_specs_ipad))

    for base, slug, price, year in [
        ('Apple Watch Ultra 2',           'apple-watch-ultra-2',           799.00, 2023),
        ('Apple Watch Series 10',         'apple-watch-series-10',         399.00, 2024),
        ('Apple Watch Series 9',          'apple-watch-series-9',          399.00, 2023),
        ('Apple Watch SE (2nd gen)',      'apple-watch-se-2',              249.00, 2023),
        ('Apple Watch Hermès Series 10',  'apple-watch-hermes-series-10', 1249.00, 2024),
    ]:
        extra.append(_refurb_tuple(base, slug, 'watch', price, year, 'S10',
                                   ['Silver', 'Space Black'], ['41mm', '45mm'],
                                   refurb_specs_watch))

    for base, slug, price, year in [
        ('AirPods Pro 2 (USB-C)',  'airpods-pro-2-usb-c',  249.00, 2023),
        ('AirPods Max',            'airpods-max',          549.00, 2020),
        ('AirPods 3 with MagSafe', 'airpods-3-magsafe',    169.00, 2022),
    ]:
        extra.append(_refurb_tuple(base, slug, 'airpods', price, year, 'H2',
                                   ['White', 'Midnight'], [],
                                   {'anc': 'Active Noise Cancellation', 'battery': 'Apple-tested'}))

    # ------------------------------------------------------------------
    # B. Education savings SKUs — bundles + per-product education prices
    # ------------------------------------------------------------------
    edu_skus = [
        ('MacBook Air 13" — Education',    'macbook-air-13',    999.00,  41.62, ['Midnight', 'Starlight', 'Space Gray', 'Silver'], ['256GB', '512GB', '1TB'], {'chip': 'M5', 'memory': '16GB', 'savings_off_retail': 100}, 2026),
        ('MacBook Air 15" — Education',    'macbook-air-15',   1199.00,  49.95, ['Midnight', 'Starlight', 'Space Gray', 'Silver'], ['256GB', '512GB', '1TB'], {'chip': 'M5', 'memory': '16GB', 'savings_off_retail': 100}, 2026),
        ('MacBook Pro 14" — Education',    'macbook-pro-14',   1599.00,  66.62, ['Space Black', 'Silver'], ['512GB', '1TB', '2TB'], {'chip': 'M5', 'memory': '24GB', 'savings_off_retail': 100}, 2026),
        ('MacBook Pro 16" — Education',    'macbook-pro-16',   2299.00,  95.79, ['Space Black', 'Silver'], ['512GB', '1TB', '2TB'], {'chip': 'M5 Pro', 'memory': '36GB', 'savings_off_retail': 200}, 2026),
        ('iMac 24" — Education',           'imac-24',          1249.00,  52.04, ['Blue', 'Green', 'Pink', 'Silver'], ['256GB', '512GB'], {'chip': 'M5', 'memory': '16GB', 'savings_off_retail': 50}, 2026),
        ('Mac mini — Education',           'mac-mini',          549.00,  22.87, ['Silver'], ['256GB', '512GB'], {'chip': 'M4', 'memory': '16GB', 'savings_off_retail': 50}, 2025),
        ('iPad Air M4 — Education',        'ipad-air-m4',       549.00,  22.87, ['Space Gray', 'Blue', 'Purple', 'Starlight'], ['128GB', '256GB', '512GB'], {'chip': 'M4', 'savings_off_retail': 50}, 2024),
        ('iPad Pro M5 — Education',        'ipad-pro-m5',       899.00,  37.45, ['Space Black', 'Silver'], ['256GB', '512GB', '1TB'], {'chip': 'M5', 'savings_off_retail': 100}, 2025),
        ('iPad (10th gen) — Education',    'ipad-10',           329.00,  13.70, ['Blue', 'Pink', 'Yellow', 'Silver'], ['64GB', '256GB'], {'chip': 'A14 Bionic', 'savings_off_retail': 20}, 2022),
    ]
    for name, slug, price, mp, colors, storage, specs, year in edu_skus:
        extra.append(_edu_bundle_tuple(name, slug, price, mp, colors, storage, specs, year))

    # Education AppleCare add-on bundle SKUs — single bundled price
    for term, slug, price in [
        ('Education AppleCare+ for MacBook Air',    'applecare-edu-macbook-air',    179.00),
        ('Education AppleCare+ for MacBook Pro 14', 'applecare-edu-macbook-pro-14', 219.00),
        ('Education AppleCare+ for MacBook Pro 16', 'applecare-edu-macbook-pro-16', 269.00),
        ('Education AppleCare+ for iPad Pro',       'applecare-edu-ipad-pro',        99.00),
        ('Education AppleCare+ for iPad Air',       'applecare-edu-ipad-air',        79.00),
        ('Education AppleCare+ for iMac',           'applecare-edu-imac',           149.00),
    ]:
        extra.append((term, f'education-savings-{slug}', 'accessories', 'education',
                      'Education AppleCare+. Verified via UNiDAYS.',
                      f'{term} — 3-year hardware coverage, unlimited accidental damage incidents, and 24/7 Apple Specialist support, at the education price.',
                      price, None, ['Education'], [], {'term': '3 years', 'audience': 'Education'}, 2026, ''))

    # ------------------------------------------------------------------
    # C. Watch bands — rainbow extension (R4 color matrix)
    # ------------------------------------------------------------------
    sizes = (('41mm', 'Apple Watch 40/41mm'),
             ('45mm', 'Apple Watch 44/45/46mm'),
             ('49mm', 'Apple Watch Ultra 49mm'))
    r4_band_colors = ['Cement Gray', 'Powder Blue', 'Apricot', 'Aubergine',
                      'Sage Green', 'Coral Pink', 'Indigo Twilight']
    extra += _band_matrix('Sport Band R4',  sizes, r4_band_colors, 49.00)
    extra += _band_matrix('Sport Loop R4',  sizes, r4_band_colors, 49.00)
    extra += _band_matrix('Braided Loop R4', (sizes[0], sizes[1]),
                          ['Charcoal', 'Cement Gray', 'Coral Pink'], 99.00)

    # Today-at-Apple themed limited-edition bands (real Apple drops every season)
    for season, color in [
        ('Pride Edition 2025', 'Rainbow'),
        ('International Womens Day 2025', 'Lilac'),
        ('Unity 2025', 'Black-Gold'),
        ('Black Unity 2025', 'Pan-African'),
    ]:
        slug = f'sport-band-41mm-{season.lower().replace(" ", "-")}-r4'
        extra.append(_watch_band_tuple(f'Sport Band - 41mm {season}', slug, color, 49.00, 2025,
                                       'Apple Watch 40/41mm'))
        slug45 = f'sport-band-45mm-{season.lower().replace(" ", "-")}-r4'
        extra.append(_watch_band_tuple(f'Sport Band - 45mm {season}', slug45, color, 49.00, 2025,
                                       'Apple Watch 44/45/46mm'))

    # ------------------------------------------------------------------
    # D. iPhone 17 / Air / 16 series cases — complete color matrix
    # ------------------------------------------------------------------
    case_matrix = [
        ('iPhone 17 Pro Max',  'iphone-17-pro-max',  ['Black', 'Storm Blue', 'Plum', 'Cypress', 'Natural Tan', 'Stone Gray', 'Light Pink']),
        ('iPhone 17 Plus',     'iphone-17-plus',     ['Black', 'Storm Blue', 'Light Pink', 'Cypress', 'Sun Yellow']),
        ('iPhone Air',         'iphone-air',         ['Midnight', 'Starlight', 'Green', 'Blue', 'Pink', 'Apricot']),
    ]
    for model, model_slug, colors in case_matrix:
        for c in colors:
            extra.append(_case_tuple(
                f'{model} Silicone Case with MagSafe - {c} (R4)',
                f'{model_slug}-silicone-r4-{c.lower().replace(" ", "-")}',
                model, c, 49.00))
        for c in colors[:3]:
            extra.append(_case_tuple(
                f'{model} Fine Woven Case with MagSafe - {c} (R4)',
                f'{model_slug}-fine-woven-r4-{c.lower().replace(" ", "-")}',
                model, c, 59.00, kind='Fine Woven Case'))
        # Clear case per model
        extra.append(_case_tuple(
            f'{model} Clear Case with MagSafe (R4)',
            f'{model_slug}-clear-magsafe-r4', model, 'Clear', 49.00,
            kind='Clear Case'))

    # ------------------------------------------------------------------
    # E. Smart Folio / Magic Keyboard for iPad — R4 color set
    # ------------------------------------------------------------------
    folio_colors = ['Charcoal Gray', 'Light Violet', 'Denim', 'Sage', 'Marigold', 'Storm Blue']
    for model, model_slug in [
        ('iPad Pro 11" M4',  'ipad-pro-11-m4'),
        ('iPad Pro 13" M4',  'ipad-pro-13-m4'),
        ('iPad Air 11" M4',  'ipad-air-11-m4'),
        ('iPad Air 13" M4',  'ipad-air-13-m4'),
    ]:
        for c in folio_colors:
            slug = f'smart-folio-r4-{model_slug}-{c.lower().replace(" ", "-")}'
            extra.append((f'Smart Folio for {model} - {c}', slug, 'accessories', 'ipad-folio',
                          'Smart Folio cover.',
                          f'Smart Folio for {model} in {c}. Front and back cover with multiple viewing angles. '
                          f'Auto-wake and sleep. Magnetic attachment.',
                          79.00, None, [c], [], {'compat': model, 'color': c}, 2025, ''))
    # Magic Keyboard for iPad Pro M4 in two colors
    for c in ['White', 'Black']:
        extra.append((f'Magic Keyboard for iPad Pro 11" M4 - {c} (R4)',
                      f'magic-keyboard-r4-ipad-pro-11-m4-{c.lower()}',
                      'accessories', 'ipad-keyboard',
                      'Backlit Magic Keyboard with trackpad.',
                      f'Magic Keyboard for iPad Pro 11" (M4) in {c}. Floating cantilever design, backlit keys, '
                      f'glass trackpad, function-key row, and USB-C passthrough charging.',
                      299.00, None, [c], [], {'compat': 'iPad Pro 11" M4', 'color': c}, 2024, ''))
        extra.append((f'Magic Keyboard for iPad Pro 13" M4 - {c} (R4)',
                      f'magic-keyboard-r4-ipad-pro-13-m4-{c.lower()}',
                      'accessories', 'ipad-keyboard',
                      'Backlit Magic Keyboard with trackpad.',
                      f'Magic Keyboard for iPad Pro 13" (M4) in {c}. Floating cantilever design, backlit keys, '
                      f'glass trackpad, function-key row, and USB-C passthrough charging.',
                      349.00, None, [c], [], {'compat': 'iPad Pro 13" M4', 'color': c}, 2024, ''))

    # ------------------------------------------------------------------
    # F. Chargers, cables, adapters — extended catalog
    # ------------------------------------------------------------------
    # MagSafe + USB-C cables in 1m / 2m / braided variants
    for length, price in [('1m', 19.0), ('1m Braided', 29.0),
                          ('2m', 29.0), ('2m Braided', 39.0),
                          ('3m', 39.0), ('3m Braided', 49.0)]:
        slug = f'usb-c-charge-cable-{length.lower().replace(" ", "-")}-r4'
        extra.append((f'USB-C Charge Cable ({length}) (R4)', slug, 'accessories', 'cable',
                      'Charge and sync cable.',
                      f'USB-C Charge Cable {length}. Connects USB-C-equipped devices for fast charging and data transfer up to 480Mbps.',
                      price, None, ['White'], [], {'length': length, 'spec': 'USB 2.0, 60W'}, 2024, ''))
    for length, price in [('1m', 29.0), ('1m Braided', 39.0),
                          ('2m', 39.0), ('2m Braided', 49.0)]:
        slug = f'thunderbolt-4-cable-{length.lower().replace(" ", "-")}-r4'
        extra.append((f'Thunderbolt 4 (USB-C) Pro Cable ({length}) (R4)', slug, 'accessories', 'cable',
                      'Thunderbolt 4 Pro cable.',
                      f'Thunderbolt 4 Pro Cable {length}. Up to 40Gb/s Thunderbolt and 100W charging. '
                      f'Compatible with all USB-C devices.',
                      price, None, ['Black'], [], {'length': length, 'spec': 'TB4 40Gbps'}, 2024, ''))
    # Color variants of MagSafe Charger (1m, 2m woven)
    for length, color, price in [
        ('1m woven', 'Midnight',    39.0),
        ('1m woven', 'Starlight',   39.0),
        ('1m woven', 'Cypress',     39.0),
        ('1m woven', 'Storm Blue',  39.0),
        ('2m woven', 'Midnight',    49.0),
        ('2m woven', 'Starlight',   49.0),
        ('2m woven', 'Cypress',     49.0),
        ('2m woven', 'Storm Blue',  49.0),
    ]:
        slug = f'magsafe-charger-{length.replace(" ", "-")}-{color.lower().replace(" ", "-")}-r4'
        extra.append((f'MagSafe Charger ({length}) - {color} (R4)', slug, 'accessories', 'charger',
                      'MagSafe wireless charger.',
                      f'MagSafe Charger {length} in {color}. Up to 25W fast wireless charging with a compatible 30W or higher USB-C adapter.',
                      price, None, [color], [], {'output': 'MagSafe 25W', 'length': length}, 2024, ''))
    # Worldwide travel adapter colors + extra wattage adapters
    for slug, name, watts in [
        ('usb-c-power-adapter-30w-r4',  'USB-C Power Adapter 30W',          30),
        ('usb-c-power-adapter-60w-r4',  'USB-C Power Adapter 60W',          60),
        ('usb-c-power-adapter-96w-r4',  'USB-C Power Adapter 96W',          96),
        ('usb-c-power-adapter-140w-r4', 'USB-C Power Adapter 140W (Pro)',  140),
    ]:
        extra.append(_power_tuple(name, slug, watts, year=2025))

    # ------------------------------------------------------------------
    # G. Business + bulk volume bundles
    # ------------------------------------------------------------------
    for seats, slug, price in [
        (25,  'apple-business-essentials-25-seat',  399.0),
        (50,  'apple-business-essentials-50-seat',  749.0),
        (100, 'apple-business-essentials-100-seat', 1399.0),
        (250, 'apple-business-essentials-250-seat', 3299.0),
        (500, 'apple-business-essentials-500-seat', 6299.0),
    ]:
        extra.append((f'Apple Business Essentials — {seats}-seat plan', slug, 'accessories', 'business',
                      f'Device management for {seats} employees.',
                      f'Apple Business Essentials covers up to {seats} employees. Includes device management, 24/7 Apple Support, '
                      f'iCloud storage, and AppleCare+ for Business options. Volume billing with monthly invoicing.',
                      price, None, ['Business'], [], {'seats': seats, 'audience': 'Business'}, 2026, ''))

    for slug, name, qty, price in [
        ('volume-bundle-macbook-air-13-10pk',  'Volume Bundle: 10× MacBook Air 13"', 10, 9499.0),
        ('volume-bundle-macbook-air-13-25pk',  'Volume Bundle: 25× MacBook Air 13"', 25, 22999.0),
        ('volume-bundle-ipad-air-m4-25pk',     'Volume Bundle: 25× iPad Air M4',     25, 12999.0),
        ('volume-bundle-iphone-16-50pk',       'Volume Bundle: 50× iPhone 16',       50, 36999.0),
        ('volume-bundle-imac-24-10pk',         'Volume Bundle: 10× iMac 24"',        10, 11999.0),
    ]:
        extra.append((name, slug, 'accessories', 'business',
                      f'Volume Pricing — {qty}-pack for Apple at Work customers.',
                      f'{name}. Available exclusively through the Apple Business Program. Contact 1-800-854-3680 for AFS lease options, '
                      f'volume discounts, zero-touch deployment, and Apple Business Manager onboarding.',
                      price, None, ['Business'], [], {'qty': qty, 'audience': 'Business'}, 2026, ''))

    # ------------------------------------------------------------------
    # H. Accessibility-themed + Today-at-Apple session add-ons
    # ------------------------------------------------------------------
    for slug, name, price, desc in [
        ('switch-control-jelly-bean-switch',         'Jelly Bean Twist Switch (for Switch Control)',         59.0,
         'Single-action switch with 3.5mm jack. Compatible with iPad and iPhone Switch Control accessibility feature.'),
        ('rj-cooper-bluetooth-supertalker',          'RJ Cooper Bluetooth SuperTalker',                       89.0,
         'Augmentative and alternative communication (AAC) Bluetooth keyboard for iPad. Works with the iOS Accessibility Speak Selection feature.'),
        ('logitech-adaptive-gaming-kit',             'Logitech Adaptive Gaming Kit',                          99.0,
         'Kit of accessibility buttons for use with the Xbox Adaptive Controller and Apple Game Controller assistive features.'),
        ('made-for-iphone-hearing-aid-pair',         'Made for iPhone Hearing Aid Pair (Cochlear / Resound)', 2399.0,
         'Pair of Made for iPhone (MFi) hearing aids. Stream audio directly from iPhone, take calls, and adjust via the Hearing accessibility menu.'),
    ]:
        extra.append((name, slug, 'accessories', 'accessibility',
                      'Accessibility add-on.',
                      desc, price, None, ['Accessibility'], [],
                      {'audience': 'Accessibility', 'platform': 'iOS / iPadOS / macOS'}, 2024, ''))

    # ------------------------------------------------------------------
    # I. HomeKit / Smart home — third-party accessories sold by Apple
    # ------------------------------------------------------------------
    for slug, name, brand, kind, price in [
        ('eve-motion-sensor-r4',          'Eve Motion (HomeKit Motion Sensor)',         'Eve',       'sensor',    49.95),
        ('eve-door-window-r4',            'Eve Door & Window Sensor',                   'Eve',       'sensor',    39.95),
        ('eve-water-guard-r4',            'Eve Water Guard',                            'Eve',       'sensor',    89.95),
        ('eve-thermo-r4',                 'Eve Thermo (HomeKit Radiator Valve)',        'Eve',       'thermostat',79.95),
        ('eve-degree-r4',                 'Eve Degree (Weather Sensor)',                'Eve',       'sensor',    69.95),
        ('philips-hue-bridge-r4',         'Philips Hue Bridge',                         'Philips',   'hub',       59.99),
        ('philips-hue-go-portable-r4',    'Philips Hue Go Portable Light',              'Philips',   'lamp',      89.99),
        ('philips-hue-ambiance-bulb-r4',  'Philips Hue White and Color Ambiance A19 Bulb','Philips', 'bulb',      49.99),
        ('philips-hue-light-strip-r4',    'Philips Hue Lightstrip Plus (2m)',           'Philips',   'lightstrip',89.99),
        ('nanoleaf-lines-starter-r4',     'Nanoleaf Lines Smarter Kit (15-piece)',      'Nanoleaf',  'lightstrip',199.99),
        ('nanoleaf-shapes-triangles-r4',  'Nanoleaf Shapes Triangles Smarter Kit',      'Nanoleaf',  'lightstrip',199.99),
        ('nanoleaf-essentials-bulb-r4',   'Nanoleaf Essentials A19 Smart Bulb',         'Nanoleaf',  'bulb',      19.99),
        ('aqara-hub-m2-r4',               'Aqara Hub M2 (Matter, Thread)',              'Aqara',     'hub',       49.99),
        ('aqara-camera-hub-g3-r4',        'Aqara Camera Hub G3 (HomeKit Secure Video)', 'Aqara',     'camera',   109.99),
        ('aqara-presence-sensor-fp2-r4',  'Aqara Presence Sensor FP2',                  'Aqara',     'sensor',    82.99),
        ('logitech-circle-view-r4',       'Logitech Circle View Camera (HomeKit Secure Video)','Logitech','camera',159.99),
        ('netatmo-smart-thermostat-r4',   'Netatmo Smart Thermostat',                   'Netatmo',   'thermostat',179.99),
        ('netatmo-smart-doorbell-r4',     'Netatmo Smart Video Doorbell',               'Netatmo',   'camera',   299.99),
        ('level-lock-plus-r4',            'Level Lock+ (Home Key)',                     'Level',     'lock',     329.00),
        ('yale-assure-lock-2-r4',         'Yale Assure Lock 2 (Home Key)',              'Yale',      'lock',     279.99),
        ('schlage-encode-plus-r4',        'Schlage Encode Plus Smart WiFi Deadbolt',    'Schlage',   'lock',     299.99),
        ('lutron-caseta-starter-r4',      'Lutron Caséta Smart Lighting Starter Kit',   'Lutron',    'switch',   149.95),
        ('myq-smart-garage-r4',           'myQ Smart Garage Hub (HomeKit)',             'myQ',       'garage',    49.98),
        ('eve-energy-smart-plug-r4',      'Eve Energy Smart Plug',                      'Eve',       'plug',      39.95),
        ('iottie-magsafe-mount-r4',       'iOttie iTap Magnetic 2 MagSafe Car Mount',   'iOttie',    'mount',     34.99),
    ]:
        extra.append((name, slug, 'accessories', 'homekit',
                      f'{brand} {kind} for the Apple Home app.',
                      f'{name}. Connects to the Apple Home app on iPhone, iPad, Mac, HomePod, or Apple TV. '
                      f'Works with Siri shortcuts. Matter and Thread support where available.',
                      price, None, ['White'], [],
                      {'brand': brand, 'kind': kind, 'platform': 'HomeKit'}, 2025, ''))

    # ------------------------------------------------------------------
    # J. Audio + TV accessories
    # ------------------------------------------------------------------
    for slug, name, price, desc in [
        ('apple-tv-4k-2024-siri-remote-r4',  'Siri Remote (USB-C, 3rd generation)',                          69.0,
         'Lightweight rechargeable Siri Remote with a touch-enabled clickpad, dedicated Siri and back buttons. USB-C charging.'),
        ('apple-tv-4k-ethernet-r4',          'Apple TV 4K (Wi-Fi + Ethernet, 128GB)',                       149.0,
         'Apple TV 4K with Ethernet, Thread support, and 128GB storage. Powered by A15 Bionic.'),
        ('homepod-mini-orange-r4',           'HomePod mini - Orange',                                        99.0,
         'Room-filling sound in a compact design. Audio sharing across multiple HomePods, with U1 chip for handoff from iPhone.'),
        ('homepod-mini-yellow-r4',           'HomePod mini - Yellow',                                        99.0,
         'Room-filling sound in a compact design. Audio sharing across multiple HomePods, with U1 chip for handoff from iPhone.'),
        ('homepod-mini-blue-r4',             'HomePod mini - Blue',                                          99.0,
         'Room-filling sound in a compact design. Audio sharing across multiple HomePods, with U1 chip for handoff from iPhone.'),
        ('apple-tv-remote-loop-r4',          'Apple TV Remote Loop',                                         13.0,
         'Tether loop for the Siri Remote. Prevents drops during use.'),
        ('beats-pill-statement-red-r4',      'Beats Pill - Statement Red (R4)',                             149.99,
         'Pill-shaped wireless speaker. Up to 24 hours of battery. Lossless audio over USB-C. iOS Find My support.'),
        ('beats-pill-matte-black-r4',        'Beats Pill - Matte Black (R4)',                               149.99,
         'Pill-shaped wireless speaker. Up to 24 hours of battery. Lossless audio over USB-C. iOS Find My support.'),
        ('belkin-soundform-immerse-r4',      'Belkin SoundForm Immerse with MagSafe Charger',                89.99,
         'Bluetooth speaker doubling as a MagSafe charger for iPhone. Spatial Audio playback for FaceTime.'),
        ('sonos-era-300-airplay2-r4',        'Sonos Era 300 (AirPlay 2)',                                   449.0,
         'Spatial Audio speaker with AirPlay 2. Tune Sonos rooms with the Sonos app and group with HomePod via Apple Music.'),
    ]:
        extra.append((name, slug, 'audio', 'tv-audio',
                      desc[:80], desc, price, None, ['Default'], [],
                      {'category': 'audio'}, 2024, ''))

    # ------------------------------------------------------------------
    # K. iPhone protection — screen protectors + lens kits
    # ------------------------------------------------------------------
    for model_slug, model, price in [
        ('iphone-17-pro-max',  'iPhone 17 Pro Max',  44.95),
        ('iphone-17-pro',      'iPhone 17 Pro',      44.95),
        ('iphone-17',          'iPhone 17',          39.95),
        ('iphone-air',         'iPhone Air',         39.95),
        ('iphone-16-pro-max',  'iPhone 16 Pro Max',  44.95),
        ('iphone-16-pro',      'iPhone 16 Pro',      44.95),
        ('iphone-15-pro-max',  'iPhone 15 Pro Max',  44.95),
        ('iphone-15-pro',      'iPhone 15 Pro',      44.95),
    ]:
        extra.append((f'Belkin UltraGlass 2 Screen Protector for {model}',
                      f'belkin-ultraglass-2-{model_slug}-r4', 'accessories', 'iphone-protection',
                      'Tempered-glass screen protector.',
                      f'Belkin UltraGlass 2 with Magnetic Tray Alignment for {model}. Anti-microbial coating, scratch resistant. '
                      f'Compatible with Face ID and Action button.',
                      price, None, ['Clear'], [],
                      {'compat': model, 'kind': 'Screen Protector'}, 2025, ''))
        extra.append((f'Moment Lens Mount and Filter Kit for {model}',
                      f'moment-lens-mount-{model_slug}-r4', 'accessories', 'iphone-protection',
                      'Pro mount with magnetic CPL/ND filters.',
                      f'Moment lens mount system with magnetic CPL and ND filters for {model}. Connect M-series lenses for telephoto, anamorphic, and macro.',
                      89.99, None, ['Black'], [],
                      {'compat': model, 'kind': 'Lens Mount'}, 2025, ''))

    # ------------------------------------------------------------------
    # L. Watch chargers + docks
    # ------------------------------------------------------------------
    for slug, name, price, desc in [
        ('apple-watch-magnetic-charger-1m-r4',    'Apple Watch Magnetic Fast Charger to USB-C Cable (1 m)', 29.0,
         'Magnetic charging puck and 1-meter USB-C cable. Fast charges Apple Watch Series 7 and later.'),
        ('apple-watch-magnetic-charger-2m-r4',    'Apple Watch Magnetic Fast Charger to USB-C Cable (2 m)', 39.0,
         'Magnetic charging puck and 2-meter USB-C cable. Fast charges Apple Watch Series 7 and later.'),
        ('apple-watch-dock-leather-saddle-r4',    'Apple Watch Travel Dock - Saddle Brown Leather',         59.0,
         'Hand-finished leather travel dock with integrated cable management for Apple Watch.'),
        ('apple-watch-dock-leather-midnight-r4',  'Apple Watch Travel Dock - Midnight Leather',             59.0,
         'Hand-finished leather travel dock with integrated cable management for Apple Watch.'),
        ('nomad-apple-watch-charging-stand-r4',   'Nomad Apple Watch Charging Stand',                       79.95,
         'Aluminum charging stand for Apple Watch with weighted base and integrated USB-C cable.'),
        ('apple-watch-magsafe-duo-r4',            'Apple MagSafe Duo Charger for Apple Watch + iPhone',     129.0,
         'Foldable MagSafe Duo charger. Charges iPhone and Apple Watch simultaneously.'),
    ]:
        extra.append((name, slug, 'accessories', 'charger',
                      desc[:80], desc, price, None, ['Default'], [],
                      {'kind': 'Watch Charger'}, 2024, ''))

    # ------------------------------------------------------------------
    # M. Additional refurbished SKUs (HomePod, Apple TV, Vision Pro)
    # ------------------------------------------------------------------
    for base, slug, price, year in [
        ('HomePod (2nd generation)', 'homepod-2',                   299.00, 2023),
        ('HomePod mini',             'homepod-mini',                 99.00, 2020),
        ('Apple TV 4K (3rd gen)',    'apple-tv-4k-3rd-gen',         129.00, 2022),
        ('Apple Vision Pro 256GB',   'vision-pro-256gb',           3499.00, 2024),
        ('Apple Vision Pro 512GB',   'vision-pro-512gb',           3699.00, 2024),
        ('Apple Vision Pro 1TB',     'vision-pro-1tb',             3899.00, 2024),
    ]:
        extra.append(_refurb_tuple(base, slug, 'audio' if 'HomePod' in base else 'vision' if 'Vision' in base else 'tv',
                                   price, year, 'A15',
                                   ['Default'], [], {'condition': 'Apple Certified'}))

    # ------------------------------------------------------------------
    # N. Final fill — Watch bumpers, iPhone crossbody straps, Pencil tips,
    #    and Mac peripherals to bring the catalog past 900 SKUs.
    # ------------------------------------------------------------------
    for slug, name, price, desc in [
        ('apple-watch-bumper-41mm-clear-r4',  'Apple Watch Bumper Case - 41mm Clear',                       29.0,
         'Slim, MagSafe-compatible bumper case for Apple Watch 40/41mm. Protects edges without obstructing buttons.'),
        ('apple-watch-bumper-45mm-clear-r4',  'Apple Watch Bumper Case - 45mm Clear',                       29.0,
         'Slim, MagSafe-compatible bumper case for Apple Watch 44/45/46mm. Protects edges without obstructing buttons.'),
        ('apple-watch-bumper-49mm-black-r4',  'Apple Watch Ultra Bumper Case - 49mm Black',                 39.0,
         'Reinforced rubber bumper for Apple Watch Ultra 49mm. Adventure-grade impact protection.'),
        ('apple-pencil-pro-tips-r4',          'Apple Pencil Pro Replacement Tips (4-pack)',                 19.0,
         'Four replacement tips for Apple Pencil Pro. Compatible with iPad Pro M4, iPad Air M4, and Apple Pencil (2nd generation).'),
        ('apple-pencil-usb-c-tips-r4',        'Apple Pencil (USB-C) Replacement Tips (4-pack)',             15.0,
         'Four replacement tips for Apple Pencil (USB-C). Pixel-perfect precision and tilt sensitivity preserved.'),
        ('magic-mouse-black-r4',              'Magic Mouse - Black (R4)',                                   99.0,
         'Apple Magic Mouse, redesigned with USB-C charging. Black aluminum body. Multi-touch surface for swipe and scroll gestures.'),
        ('magic-trackpad-black-r4',           'Magic Trackpad - Black (R4)',                                129.0,
         'Apple Magic Trackpad with Force Touch and Multi-Touch. Black aluminum. USB-C charging.'),
        ('magic-keyboard-numeric-black-r4',   'Magic Keyboard with Numeric Keypad - Black (R4)',            149.0,
         'Magic Keyboard with Numeric Keypad and dedicated function-key row. Black aluminum. USB-C connector.'),
        ('magic-keyboard-touch-id-black-r4',  'Magic Keyboard with Touch ID and Numeric Keypad - Black',    199.0,
         'Magic Keyboard with Touch ID and Numeric Keypad. Black anodized aluminum. Compatible with Apple silicon Macs.'),
        ('studio-display-vesa-r4',            'Studio Display - VESA Mount Adapter',                        1599.0,
         '27-inch 5K Retina display with VESA mount adapter. 12MP Ultra Wide camera and six-speaker sound system.'),
        ('iphone-crossbody-strap-marigold-r4','iPhone Crossbody Strap - Marigold',                          59.0,
         'MagSafe-compatible crossbody strap. Marigold color. Magnetic closure with iPhone Cases.'),
        ('iphone-crossbody-strap-storm-r4',   'iPhone Crossbody Strap - Storm Blue',                        59.0,
         'MagSafe-compatible crossbody strap. Storm Blue color. Magnetic closure with iPhone Cases.'),
        ('iphone-crossbody-strap-cypress-r4', 'iPhone Crossbody Strap - Cypress',                           59.0,
         'MagSafe-compatible crossbody strap. Cypress color. Magnetic closure with iPhone Cases.'),
        ('iphone-crossbody-strap-light-pink-r4','iPhone Crossbody Strap - Light Pink',                      59.0,
         'MagSafe-compatible crossbody strap. Light Pink color. Magnetic closure with iPhone Cases.'),
        ('iphone-fineWoven-folio-marigold-r4','iPhone Fine Woven Folio - Marigold',                         79.0,
         'Fine Woven folio with card slot. Marigold color. Wakes and sleeps your iPhone when opened or closed.'),
        ('iphone-fineWoven-folio-evergreen-r4','iPhone Fine Woven Folio - Evergreen',                       79.0,
         'Fine Woven folio with card slot. Evergreen color. Wakes and sleeps your iPhone when opened or closed.'),
        ('apple-watch-link-bracelet-titanium-r4','Apple Watch Link Bracelet - Titanium (45mm)',             449.0,
         'Polished titanium Link Bracelet for Apple Watch. Removable links for size adjustment. Premium butterfly closure.'),
        ('apple-watch-modern-buckle-deep-r4', 'Apple Watch Modern Buckle - Deep Sea Blue',                  149.0,
         'Granada leather Modern Buckle in Deep Sea Blue. Magnetic closure for easy on/off.'),
        ('apple-watch-leather-link-saddle-r4','Apple Watch Leather Link - Saddle Brown (Medium)',           99.0,
         'Saddle Brown leather link with hidden magnets. Adjusts automatically for a precise fit on the wrist.'),
        ('apple-watch-leather-link-evergreen-r4','Apple Watch Leather Link - Evergreen (Medium)',           99.0,
         'Evergreen leather link with hidden magnets. Adjusts automatically for a precise fit on the wrist.'),
        ('belkin-iphone-stand-magsafe-r4',    'Belkin BoostCharge Pro 3-in-1 Wireless MagSafe Stand',       149.95,
         '3-in-1 charging stand for iPhone (MagSafe), Apple Watch, and AirPods. Officially MagSafe-certified.'),
        ('twelve-south-bookarc-r4',           'Twelve South BookArc for MacBook',                            59.99,
         'Vertical aluminum stand for MacBook Air or MacBook Pro. Clears desk space and improves airflow.'),
        ('twelve-south-hirise-pro-r4',        'Twelve South HiRise Pro for MacBook',                         99.99,
         'Adjustable aluminum laptop stand for MacBook with integrated USB-C cable pass-through.'),
        ('moft-snap-on-magsafe-r4',           'MOFT Snap-On MagSafe Wallet & Stand',                         24.99,
         'Foldable MagSafe wallet with built-in stand. Holds up to three cards and props iPhone in landscape or portrait.'),
        ('peak-design-mobile-tripod-r4',      'Peak Design Mobile Tripod (MagSafe)',                         79.95,
         'Slim aluminum mobile tripod with MagSafe attachment. Pairs with iPhone for Cinematic-mode video.'),
    ]:
        extra.append((name, slug, 'accessories', 'misc',
                      desc[:80], desc, price, None, ['Default'], [],
                      {'category': 'accessory'}, 2025, ''))

    return extra


EXTRA_PRODUCTS_R4 = _extend_r4()


# ---------------------------------------------------------------------------
# R5 expansion — deeper specs (environment_report, accessibility_features,
# in_box_contents, whats_new) plus broader catalog coverage.
# ---------------------------------------------------------------------------

def _r5_deepen(specs, env=None, a11y=None, in_box=None, whats_new=None):
    """Augment a specs dict with the four R5 depth keys."""
    out = dict(specs)
    out['environment_report'] = env or (
        'Made with 30%+ recycled content by weight. Arsenic-free display glass, mercury-free, BFR/PVC/beryllium-free. '
        'Final assembly uses 100% renewable electricity. Packaging is 100% fiber-based and Forest Stewardship Council certified.'
    )
    out['accessibility_features'] = a11y or [
        'VoiceOver', 'Zoom', 'Dynamic Type', 'Reduce Motion', 'Voice Control',
        'Switch Control', 'Live Captions', 'AssistiveTouch'
    ]
    out['in_box_contents'] = in_box or ['Product', 'USB-C Charge Cable (1 m)', 'Documentation']
    out['whats_new'] = whats_new or 'R5 polish — extended color matrix, faster wireless charging, and Find My network support.'
    return out


def _extend_r5():
    """R5 expansion — push catalog from ~900 to 1400+ SKUs with depth-focused
    fields (environment_report, accessibility_features, in_box_contents,
    whats_new) and coverage for trade-in/AppleCare-coverage/repair-status/
    Apple-Card/Wallet/Find-My/Family-Sharing task lines."""
    extra = []

    # ------------------------------------------------------------------
    # A. AppleCare+ coverage SKUs for every flagship + recent generation.
    # ------------------------------------------------------------------
    applecare_catalog = [
        # (display_name, slug_suffix, device_class, price_2yr, price_monthly)
        ('AppleCare+ for iPhone 17 Pro Max',  'iphone-17-pro-max',    'iphone',  269.0,  13.49),
        ('AppleCare+ for iPhone 17 Plus',     'iphone-17-plus',       'iphone',  219.0,  10.99),
        ('AppleCare+ for iPhone 17',          'iphone-17',            'iphone',  199.0,   9.99),
        ('AppleCare+ for iPhone 17e',         'iphone-17e',           'iphone',  149.0,   7.49),
        ('AppleCare+ for iPhone Air',         'iphone-air',           'iphone',  199.0,   9.99),
        ('AppleCare+ for iPhone 16 Pro Max',  'iphone-16-pro-max',    'iphone',  269.0,  13.49),
        ('AppleCare+ for iPhone 16 Plus',     'iphone-16-plus',       'iphone',  219.0,  10.99),
        ('AppleCare+ for iPhone 16',          'iphone-16',            'iphone',  199.0,   9.99),
        ('AppleCare+ for iPhone 15 Pro Max',  'iphone-15-pro-max',    'iphone',  269.0,  13.49),
        ('AppleCare+ for iPhone 15 Plus',     'iphone-15-plus',       'iphone',  219.0,  10.99),
        ('AppleCare+ for iPhone 15',          'iphone-15',            'iphone',  199.0,   9.99),
        ('AppleCare+ for iPhone 14 Pro Max',  'iphone-14-pro-max',    'iphone',  269.0,  13.49),
        ('AppleCare+ for iPhone 14 Plus',     'iphone-14-plus',       'iphone',  219.0,  10.99),
        ('AppleCare+ for iPhone 14',          'iphone-14',            'iphone',  199.0,   9.99),
        ('AppleCare+ for iPhone 13 Pro Max',  'iphone-13-pro-max',    'iphone',  269.0,  13.49),
        ('AppleCare+ for iPhone 13 mini',     'iphone-13-mini',       'iphone',  149.0,   7.49),
        ('AppleCare+ for iPhone SE',          'iphone-se-3',          'iphone',  129.0,   6.49),
        ('AppleCare+ for MacBook Pro 16',     'macbook-pro-16',       'mac',     499.0,  21.99),
        ('AppleCare+ for MacBook Pro 14',     'macbook-pro-14',       'mac',     399.0,  17.99),
        ('AppleCare+ for MacBook Air 15',     'macbook-air-15',       'mac',     249.0,  10.99),
        ('AppleCare+ for MacBook Air 13',     'macbook-air-13',       'mac',     249.0,  10.99),
        ('AppleCare+ for iMac',               'imac-24',              'mac',     169.0,   7.49),
        ('AppleCare+ for Mac mini',           'mac-mini',              'mac',    149.0,   6.49),
        ('AppleCare+ for Mac Studio',         'mac-studio',           'mac',     299.0,  13.49),
        ('AppleCare+ for Mac Pro',            'mac-pro',              'mac',     599.0,  26.99),
        ('AppleCare+ for iPad Pro 13',        'ipad-pro-13',          'ipad',    129.0,   5.99),
        ('AppleCare+ for iPad Pro 11',        'ipad-pro-11',          'ipad',    129.0,   5.99),
        ('AppleCare+ for iPad Air 13',        'ipad-air-13',          'ipad',     99.0,   4.49),
        ('AppleCare+ for iPad Air 11',        'ipad-air-11',          'ipad',     99.0,   4.49),
        ('AppleCare+ for iPad',               'ipad-10',              'ipad',     69.0,   3.49),
        ('AppleCare+ for iPad mini',          'ipad-mini-7',          'ipad',     69.0,   3.49),
        ('AppleCare+ for Apple Watch Series 11', 'watch-series-11',   'watch',    79.0,   3.49),
        ('AppleCare+ for Apple Watch SE',     'watch-se-2',           'watch',    49.0,   2.49),
        ('AppleCare+ for Apple Watch Hermès', 'watch-hermes-10',      'watch',    99.0,   4.49),
        ('AppleCare+ for AirPods Pro 3',      'airpods-pro-3',        'airpods',  29.0,   1.49),
        ('AppleCare+ for AirPods Max 2',      'airpods-max-2',        'airpods',  39.0,   1.99),
        ('AppleCare+ for AirPods 4',          'airpods-4',            'airpods',  29.0,   1.49),
        ('AppleCare+ for HomePod',            'homepod-2',            'audio',    29.0,   1.49),
        ('AppleCare+ for HomePod mini',       'homepod-mini',         'audio',    19.0,   0.99),
        ('AppleCare+ for Apple TV 4K',        'apple-tv-4k',          'tv',       29.0,   1.49),
        ('AppleCare+ for Beats Studio Pro',   'beats-studio-pro',     'audio',    29.0,   1.49),
    ]
    for name, suffix, cls, price2, mp in applecare_catalog:
        slug = f'applecare-r5-{suffix}'
        specs = _r5_deepen({
            'term': '2-year', 'audience': 'Consumer', 'device_class': cls,
            'price_2yr_usd': price2, 'monthly_usd': mp,
            'covers': 'Unlimited accidental damage incidents, Apple-certified service and repairs, priority 24/7 access to Apple Specialists',
        }, env='AppleCare+ documentation printed on FSC-certified paper with soy-based inks. Service shipping uses carbon-neutral logistics.',
           a11y=['Service appointments accept VoiceOver bookings', 'Genius Bar offers ASL via remote interpreter on request'],
           in_box=['AppleCare+ coverage certificate (digital)', 'Quick start booklet'],
           whats_new='R5 — Adds remote-diagnostic same-day swap for iPhone Pro and AppleCare+ Coverage Lookup by serial or IMEI.')
        extra.append((name, slug, 'accessories', 'applecare',
                      f'{name}. 2 years, 24/7 priority support.',
                      f'{name}. Two years of hardware coverage, unlimited incidents of accidental damage (service fee applies), '
                      f'24/7 priority access to Apple Specialists, and battery service. Monthly billing or pay upfront — '
                      f'${price2:.2f} for 2 years, or ${mp:.2f}/mo.',
                      price2, mp, ['Service'], [], specs, 2026, ''))

    # ------------------------------------------------------------------
    # B. Apple Vision Pro accessories — Light Seal kits, head bands, etc.
    # ------------------------------------------------------------------
    vision_skus = [
        ('Light Seal Cushion (W)',  'light-seal-cushion-w',   29.0, 'Cushion W'),
        ('Light Seal Cushion (N)',  'light-seal-cushion-n',   29.0, 'Cushion N'),
        ('Light Seal Cushion (S)',  'light-seal-cushion-s',   29.0, 'Cushion S'),
        ('Light Seal Cushion (M)',  'light-seal-cushion-m',   29.0, 'Cushion M'),
        ('Light Seal (Multiple Sizes)', 'light-seal-multi',  199.0, 'Light Seal'),
        ('Solo Knit Band - Black',  'solo-knit-band-black',   99.0, 'Solo Knit Band'),
        ('Solo Knit Band - Gray',   'solo-knit-band-gray',    99.0, 'Solo Knit Band'),
        ('Solo Knit Band - Blue',   'solo-knit-band-blue',    99.0, 'Solo Knit Band'),
        ('Dual Loop Band',          'dual-loop-band',         99.0, 'Dual Loop Band'),
        ('Travel Case for Apple Vision Pro', 'vision-travel-case', 199.0, 'Travel Case'),
        ('ZEISS Optical Inserts (Readers)',  'zeiss-readers',  99.0, 'Optical Insert'),
        ('ZEISS Optical Inserts (Prescription)', 'zeiss-prescription', 149.0, 'Optical Insert'),
        ('Vision Pro Battery (External)', 'vision-battery-external', 199.0, 'Battery'),
        ('Vision Pro USB-C Charge Cable', 'vision-usbc-cable', 19.0, 'Cable'),
        ('Vision Pro 30W USB-C Power Adapter', 'vision-30w-adapter', 39.0, 'Adapter'),
        ('Vision Pro Polishing Cloth',  'vision-polishing-cloth', 19.0, 'Cloth'),
        ('Vision Pro Carry Sleeve',     'vision-carry-sleeve',     79.0, 'Sleeve'),
        ('Vision Pro Lens Cover',       'vision-lens-cover',       29.0, 'Cover'),
        ('Vision Pro Belkin Battery Holder', 'vision-belkin-battery-holder', 49.95, 'Holder'),
        ('Vision Pro Standalone Travel Tripod', 'vision-tripod', 129.0, 'Tripod'),
    ]
    for name, slug_suffix, price, kind in vision_skus:
        slug = f'vision-r5-{slug_suffix}'
        specs = _r5_deepen({'compat': 'Apple Vision Pro', 'kind': kind},
                           env='Made with recycled aluminum and 100% recycled fabric (band variants).',
                           a11y=['Compatible with VoiceOver gestures', 'Supports Dwell Control'],
                           in_box=[kind, 'Documentation'],
                           whats_new='New for R5: drop-in replacement for Vision Pro accessories with serial-locked Find My pairing.')
        extra.append((name, slug, 'accessories', 'vision-pro-accessory',
                      f'{name}. Designed for Apple Vision Pro.',
                      f'{name} for Apple Vision Pro. Pairs automatically when paired with the headset Apple ID. '
                      f'Find My-enabled. Recyclable aluminum and 100% recycled fabric (where applicable).',
                      price, None, ['Default'], [], specs, 2025, ''))

    # ------------------------------------------------------------------
    # C. Apple Card / Apple Wallet / Find My-themed SKUs.
    # ------------------------------------------------------------------
    wallet_skus = [
        ('Apple Card Titanium Welcome Kit',  'apple-card-welcome',   0.0,    'Apple Card welcome packet with activation guide and titanium card sleeve.'),
        ('Apple Card Daily Cash Boost Bundle','apple-card-daily-cash',0.0,    'Activation bundle for new Apple Card holders — 3% Daily Cash at Apple, plus partner-rate boosts.'),
        ('Apple Wallet Family Pass Kit',     'apple-wallet-family',  0.0,    'Family Pass digital kit — share keys, transit cards, and event tickets across Family Sharing members.'),
        ('Apple Wallet Hotel Key Adapter',   'apple-wallet-hotel-key',29.0,  'Adapter dongle for legacy hotel locks. Use Apple Wallet hotel keys on properties not yet supporting Tap-to-Enter.'),
        ('AirTag 1-pack',                    'airtag-1pk-r5',         29.0,  'Single AirTag. Engraving available.'),
        ('AirTag 4-pack (R5)',               'airtag-4pk-r5',         99.0,  'AirTag 4-pack. Bulk-engraving available.'),
        ('AirTag 8-pack (R5)',               'airtag-8pk-r5',        179.0,  'AirTag 8-pack. Designed for family-sized luggage sets.'),
        ('Find My Luggage Beacon',           'find-my-luggage-beacon',49.0,  'Find My-enabled luggage beacon. Lithium battery rated for travel.'),
        ('Find My Backpack Tag (Hermès)',    'find-my-backpack-hermes',299.0,'Hermès leather AirTag holder with hand-stitched edges. Pairs with Find My network.'),
        ('Find My Cycle Tag (Bike)',         'find-my-cycle-tag',     49.0,  'IP68 weatherproof AirTag mount for road and mountain bikes.'),
        ('Apple Card Cleaning Cloth',        'apple-card-cleaning-cloth',19.0,'Microfiber cloth for cleaning the titanium Apple Card and Apple devices.'),
        ('Apple Wallet Sport Strap (Black)', 'apple-wallet-sport-black',39.0,'Lightweight sport wallet for ID-only Apple Wallet days at the gym.'),
        ('Apple Wallet Pro Card Sleeve',     'apple-wallet-pro-sleeve', 49.0,'Premium leather sleeve for Apple Card, ID, and a single backup credit card. RFID-safe.'),
        ('Apple Wallet — Goldman Sachs Cobranded Welcome', 'apple-wallet-gs-welcome',0.0,'Goldman Sachs co-branded materials and travel adapter giveaway with new Apple Card activations.'),
    ]
    for name, slug_suffix, price, desc in wallet_skus:
        slug = f'wallet-r5-{slug_suffix}'
        specs = _r5_deepen({'kind': 'Wallet / Find My / Apple Card'},
                           env='Made with 90%+ recycled leather alternative or recycled titanium (Apple Card sleeve variants).',
                           a11y=['VoiceOver reads card balances inside Apple Wallet', 'Tactile notch on Apple Card sleeve aids orientation'],
                           in_box=['Item', 'Activation guide', 'Documentation'],
                           whats_new='R5 — Apple Card activation now via Wallet app QR; Find My beacons include 1-year free Apple Card cash-back boost.')
        extra.append((name, slug, 'accessories', 'apple-card-wallet',
                      f'{name}. Engineered for Apple Card and Apple Wallet.',
                      desc, price, None, ['Default'], [], specs, 2026, ''))

    # ------------------------------------------------------------------
    # D. Family Sharing / Apple One bundle SKUs.
    # ------------------------------------------------------------------
    family_bundles = [
        ('Family Sharing Starter Kit',       'family-sharing-starter',     0.0,   'Walkthrough kit to set up Family Sharing across iPhone, iPad, and Mac.'),
        ('Family Sharing — Ask to Buy Kit',  'family-sharing-ask-to-buy',  0.0,   'Activation kit for Ask to Buy approval workflows in Family Sharing.'),
        ('Family Sharing — Screen Time Card','family-sharing-screen-time', 0.0,   'Step-by-step Screen Time setup card for Family Sharing organizers.'),
        ('Family Sharing — Find My Family',  'family-sharing-find-my',     0.0,   'Find My setup card for Family Sharing. Helps locate family members on a shared map.'),
        ('Family Sharing — Shared Album Kit','family-sharing-shared-album',0.0,   'Setup kit for the Family Shared Album in Photos.'),
        ('Apple One Family — 6 month gift',  'apple-one-family-6mo-gift',  119.94,'6 months of Apple One Family. Shareable with up to 5 family members.'),
        ('Apple One Premier — 6 month gift', 'apple-one-premier-6mo-gift', 219.94,'6 months of Apple One Premier. Shareable with up to 5 family members.'),
        ('iCloud+ 2TB — 12 month',           'icloud-plus-2tb-12mo',       119.88,'12 months of iCloud+ 2TB. Shareable via Family Sharing.'),
        ('iCloud+ 6TB — 12 month',           'icloud-plus-6tb-12mo',       359.88,'12 months of iCloud+ 6TB. Shareable via Family Sharing.'),
        ('iCloud+ 12TB — 12 month',          'icloud-plus-12tb-12mo',      719.88,'12 months of iCloud+ 12TB. Shareable via Family Sharing.'),
        ('Apple Music Family — 12 month',    'apple-music-family-12mo',    179.88,'12 months of Apple Music Family. Up to 6 members.'),
        ('Apple Arcade — 12 month family',   'apple-arcade-12mo-family',    83.88,'12 months of Apple Arcade. Family Sharing supported.'),
        ('Apple Fitness+ 12 month family',   'apple-fitness-12mo-family',  119.88,'12 months of Apple Fitness+. Up to 6 family members.'),
        ('Apple News+ 12 month family',      'apple-news-12mo-family',     155.88,'12 months of Apple News+. Up to 6 family members.'),
    ]
    for name, slug_suffix, price, desc in family_bundles:
        slug = f'family-r5-{slug_suffix}'
        specs = _r5_deepen({'audience': 'Family', 'sharing': 'Family Sharing up to 6 members'},
                           env='Digital fulfillment — no physical packaging.',
                           a11y=['VoiceOver supported in all family setup flows', 'Closed Captions on Apple TV+ and Apple Fitness+'],
                           in_box=['Redemption code (email)', 'Family setup guide'],
                           whats_new='R5 — Adds Family Sharing add-member API and unified Apple One renewal calendar.')
        extra.append((name, slug, 'accessories', 'family-sharing',
                      f'{name}. Set up Family Sharing in minutes.',
                      desc, price, None, ['Family'], [], specs, 2026, ''))

    # ------------------------------------------------------------------
    # E. iPad Pro M4 Cellular + Wi-Fi variants — full storage matrix.
    # ------------------------------------------------------------------
    for size, base_price in [('11"', 999.0), ('13"', 1299.0)]:
        for storage_gb, premium in [(256, 0), (512, 200), (1024, 600), (2048, 1000)]:
            for connectivity, conn_premium, conn_slug in [
                ('Wi-Fi', 0, 'wifi'), ('Wi-Fi + Cellular', 200, 'cellular'),
            ]:
                for color, color_slug in [('Space Black', 'space-black'), ('Silver', 'silver')]:
                    storage_str = f'{storage_gb}GB' if storage_gb < 1024 else f'{storage_gb//1024}TB'
                    name = f'iPad Pro {size} (M4) {storage_str} {connectivity} - {color}'
                    slug = (f'ipad-pro-r5-{size.replace(chr(34), "")}-m4-{storage_str.lower()}-{conn_slug}-{color_slug}'
                            .replace('"', ''))
                    price = base_price + premium + conn_premium
                    specs = _r5_deepen({
                        'chip': 'M4', 'display': f'{size} Ultra Retina XDR',
                        'connectivity': connectivity, 'storage': storage_str,
                        'camera': '12MP Wide + LiDAR', 'battery': 'Up to 10 hours',
                    }, env='Made with 100% recycled aluminum enclosure, 100% recycled rare earth elements in all magnets, '
                         '100% recycled gold plating in the main logic board, and 100% renewable energy for final assembly.',
                       a11y=['Eye Tracking (iPadOS 18+)', 'VoiceOver', 'AssistiveTouch', 'Live Captions', 'Voice Control',
                             'Switch Control', 'Made for iPad hearing aids'],
                       in_box=[f'iPad Pro {size}', 'USB-C Charge Cable (1 m)', '20W USB-C Power Adapter', 'Documentation'],
                       whats_new=f'R5 — Adds Apple Intelligence on-device LLM and Find My network for AirTag alongside the iPad in Wallet.')
                    extra.append((name, slug, 'ipad', 'ipad-pro',
                                  f'iPad Pro {size}. M4 chip. Apple Pencil Pro.',
                                  f'iPad Pro {size} with M4 chip, Ultra Retina XDR display, and {connectivity}. {storage_str} storage. Color: {color}.',
                                  price, round(price/24, 2), ['Space Black', 'Silver'],
                                  ['256GB', '512GB', '1TB', '2TB'], specs, 2024, 'M4'))

    # ------------------------------------------------------------------
    # F. iPhone Pro 1TB premium tier — full color matrix.
    # ------------------------------------------------------------------
    iphone_pro_colors = ['Natural Titanium', 'Black Titanium', 'White Titanium', 'Sand Titanium', 'Desert Titanium']
    for model, model_slug, base_price, chip in [
        ('iPhone 17 Pro', 'iphone-17-pro', 1099.0, 'A19 Pro'),
        ('iPhone 17 Pro Max', 'iphone-17-pro-max', 1199.0, 'A19 Pro'),
        ('iPhone 16 Pro', 'iphone-16-pro', 999.0, 'A18 Pro'),
        ('iPhone 16 Pro Max', 'iphone-16-pro-max', 1199.0, 'A18 Pro'),
    ]:
        for storage_gb, premium in [(256, 0), (512, 200), (1024, 400)]:
            for color in iphone_pro_colors:
                storage_str = f'{storage_gb}GB' if storage_gb < 1024 else f'{storage_gb//1024}TB'
                slug = (f'{model_slug}-r5-{storage_str.lower()}-{color.lower().replace(" ", "-")}')
                name = f'{model} {storage_str} - {color}'
                price = base_price + premium
                specs = _r5_deepen({
                    'chip': chip, 'storage': storage_str, 'color': color,
                    'display': '6.3" Super Retina XDR' if 'Pro Max' not in model else '6.9" Super Retina XDR',
                    'camera': '48MP Main + 48MP Ultra Wide + 12MP Telephoto',
                    'battery': 'Up to 33 hours video playback',
                }, env='Made with 95% recycled titanium in the structural frame, 100% recycled aluminum in the thermal substructure, '
                     '100% recycled rare earth elements, 100% recycled cobalt in the battery, and packaging is 100% fiber-based.',
                   a11y=['VoiceOver', 'Action button assignable to AssistiveTouch', 'Live Captions', 'Eye Tracking', 'Personal Voice',
                         'Vehicle Motion Cues', 'Music Haptics', 'Made for iPhone hearing aids'],
                   in_box=[f'{model}', 'USB-C Charge Cable (1 m)', 'Documentation'],
                   whats_new=f'R5 — Adds Apple Intelligence on-device, Visual Intelligence, AirPods Pro 3 hearing aid feature, and Wallet hotel keys.')
                extra.append((name, slug, 'iphone', 'iphone-pro',
                              f'{model}. {chip}. Titanium.',
                              f'{name} — {chip} chip, titanium design, 48MP camera system with 8x optical-quality zoom, ProMotion display.',
                              price, round(price/24, 2), [color], [storage_str], specs, 2025 if '17' in model else 2024, chip))

    # ------------------------------------------------------------------
    # G. Trade-in promo SKUs by IMEI lookup tier.
    # ------------------------------------------------------------------
    tradein_promos = [
        ('Trade-in Promo — iPhone 13 (IMEI lookup)', 'tradein-imei-iphone-13', 240.0,
         'Instant trade-in credit for iPhone 13 by IMEI lookup. No appointment required.'),
        ('Trade-in Promo — iPhone 14 (IMEI lookup)', 'tradein-imei-iphone-14', 340.0, 'Instant trade-in credit for iPhone 14 via IMEI lookup.'),
        ('Trade-in Promo — iPhone 15 (IMEI lookup)', 'tradein-imei-iphone-15', 470.0, 'Instant trade-in credit for iPhone 15 via IMEI lookup.'),
        ('Trade-in Promo — iPhone 15 Pro (IMEI lookup)','tradein-imei-iphone-15-pro',650.0, 'Instant trade-in credit for iPhone 15 Pro via IMEI lookup.'),
        ('Trade-in Promo — iPhone 16 (IMEI lookup)', 'tradein-imei-iphone-16', 540.0, 'Instant trade-in credit for iPhone 16 via IMEI lookup.'),
        ('Trade-in Promo — iPhone 16 Pro (IMEI lookup)','tradein-imei-iphone-16-pro',720.0, 'Instant trade-in credit for iPhone 16 Pro via IMEI lookup.'),
        ('Trade-in Promo — Apple Watch S9 (IMEI lookup)','tradein-imei-watch-s9',95.0, 'Apple Watch Series 9 trade-in credit by IMEI lookup.'),
        ('Trade-in Promo — Apple Watch Ultra 2 (IMEI lookup)','tradein-imei-watch-ultra-2',280.0, 'Apple Watch Ultra 2 trade-in credit via IMEI lookup.'),
        ('Trade-in Promo — iPad Pro M2 (IMEI lookup)','tradein-imei-ipad-pro-m2',410.0, 'iPad Pro M2 trade-in credit by IMEI lookup.'),
        ('Trade-in Promo — iPad Air M2 (IMEI lookup)','tradein-imei-ipad-air-m2',280.0, 'iPad Air M2 trade-in credit by IMEI lookup.'),
        ('Trade-in Promo — MacBook Air M2 (Serial lookup)','tradein-serial-mba-m2',430.0, 'MacBook Air M2 trade-in credit via serial lookup.'),
        ('Trade-in Promo — MacBook Pro M3 (Serial lookup)','tradein-serial-mbp-m3',900.0, 'MacBook Pro M3 trade-in credit via serial lookup.'),
        ('Trade-in Promo — iMac M3 (Serial lookup)','tradein-serial-imac-m3',520.0, 'iMac M3 trade-in credit via serial lookup.'),
        ('Trade-in Promo — Mac mini M2 (Serial lookup)','tradein-serial-mac-mini-m2',230.0, 'Mac mini M2 trade-in credit via serial lookup.'),
        ('Trade-in Promo — Apple Vision Pro (Serial lookup)','tradein-serial-vision-pro',1900.0, 'Apple Vision Pro trade-in credit via serial lookup.'),
    ]
    for name, slug_suffix, price, desc in tradein_promos:
        slug = f'tradein-r5-{slug_suffix}'
        specs = _r5_deepen({'kind': 'Trade-in Promo', 'lookup_method': 'IMEI/Serial',
                            'instant_credit_usd': price},
                           env='Trade-in devices are recycled by Apple at certified e-waste recovery facilities.',
                           a11y=['Trade-in tool supports VoiceOver and Voice Control on iPhone'],
                           in_box=['Postage-paid return mailer', 'Trade-in instructions'],
                           whats_new='R5 — Adds direct IMEI lookup at /trade-in/imei with instant credit estimate and same-day Apple Gift Card delivery.')
        extra.append((name, slug, 'accessories', 'trade-in',
                      f'{name}. Apple Trade In.',
                      desc, price, None, ['Trade-in'], [], specs, 2026, ''))

    # ------------------------------------------------------------------
    # H. Pro audio — Logic Pro / Final Cut Pro / FCP for iPad add-ons.
    # ------------------------------------------------------------------
    pro_audio_skus = [
        ('Logic Pro for Mac (12-month)',    'logic-pro-mac-12mo',    49.0, 'Logic Pro for Mac — 12-month subscription with all Apple-trained sound libraries.'),
        ('Logic Pro for iPad (12-month)',   'logic-pro-ipad-12mo',   49.0, 'Logic Pro for iPad — 12-month subscription including Beat Breaker, Quick Sampler, and Live Loops.'),
        ('Final Cut Pro for Mac (12-month)','fcp-mac-12mo',          49.0, 'Final Cut Pro for Mac — 12-month subscription with all motion graphics templates.'),
        ('Final Cut Pro for iPad (12-month)','fcp-ipad-12mo',        49.0, 'Final Cut Pro for iPad — 12-month subscription with Live Drawing and Voiceover.'),
        ('Final Cut Camera Pro Kit',        'fc-camera-pro-kit',    149.0, 'Final Cut Camera Pro Kit — multi-cam Live tools for iPhone and iPad. Synced via Final Cut Pro.'),
        ('MainStage for Mac',               'mainstage-mac',         29.0, 'MainStage for Mac — Apple Loops library and live stage performance plugin pack.'),
        ('Motion for Mac',                  'motion-mac',            49.0, 'Motion for Mac — 2D and 3D motion graphics with rigging tools.'),
        ('Compressor for Mac',              'compressor-mac',        49.0, 'Compressor — advanced encoding for Final Cut Pro.'),
        ('GarageBand Educator Pack',        'garageband-educator',   29.0, 'GarageBand Educator Pack — lesson plans and shared loops for music classrooms.'),
        ('Logic Pro Sound Library Bundle',  'logic-sound-library',   29.0, 'Producer Packs, Sample Packs, and Live Loops grid templates for Logic Pro.'),
        ('Final Cut Pro Title Pack',        'fcp-title-pack',        29.0, 'Curated title and lower-third pack for Final Cut Pro.'),
        ('Pro Apps Bundle for Education',   'pro-apps-edu-bundle',  199.99,'Pro Apps Bundle for Education — Final Cut Pro, Logic Pro, MainStage, Motion, and Compressor for students.'),
    ]
    for name, slug_suffix, price, desc in pro_audio_skus:
        slug = f'pro-r5-{slug_suffix}'
        specs = _r5_deepen({'kind': 'Pro App / Subscription', 'platform': 'Mac/iPad'},
                           env='Digital fulfillment — no physical packaging. Sound libraries downloaded from CDN powered by 100% renewable energy.',
                           a11y=['VoiceOver throughout', 'Dynamic Type', 'Captions on all Apple-provided learning content',
                                 'Switch Control palette mode'],
                           in_box=['App Store redemption code (email)', 'Onboarding guide'],
                           whats_new='R5 — Adds Apple Intelligence-powered timeline assistant in Final Cut Pro and AI mastering preset in Logic Pro.')
        extra.append((name, slug, 'accessories', 'pro-app',
                      f'{name}. Designed for creators.',
                      desc, price, None, ['Default'], [], specs, 2026, ''))

    # ------------------------------------------------------------------
    # I. Sustainability / Recycled materials SKUs — explicit env_report row.
    # ------------------------------------------------------------------
    sustain_skus = [
        ('iPhone FineWoven Recycled Case (Black)',   'finewoven-recycled-black',   59.0),
        ('iPhone FineWoven Recycled Case (Mulberry)','finewoven-recycled-mulberry',59.0),
        ('iPhone FineWoven Recycled Case (Taupe)',   'finewoven-recycled-taupe',   59.0),
        ('iPhone FineWoven Recycled Case (Evergreen)','finewoven-recycled-evergreen',59.0),
        ('iPhone FineWoven Recycled Case (Pacific Blue)','finewoven-recycled-pacific',59.0),
        ('iPad Smart Folio - Recycled Fabric Edition (Storm)','smart-folio-recycled-storm',79.0),
        ('iPad Smart Folio - Recycled Fabric Edition (Sage)', 'smart-folio-recycled-sage',79.0),
        ('iPad Smart Folio - Recycled Fabric Edition (Marigold)','smart-folio-recycled-marigold',79.0),
        ('MacBook Sleeve - 100% Recycled Wool',      'macbook-sleeve-recycled-wool', 99.0),
        ('Apple Watch Modern Buckle - Recycled Leather (Coffee)','watch-modern-recycled-coffee',149.0),
        ('iPhone Crossbody Strap - 100% Recycled Yarn (Forest)','crossbody-recycled-forest',59.0),
        ('iPhone Crossbody Strap - 100% Recycled Yarn (Coral)','crossbody-recycled-coral',59.0),
        ('MagSafe Charger 1m - Recycled Plastic Edition','magsafe-recycled-1m',39.0),
        ('MagSafe Charger 2m - Recycled Plastic Edition','magsafe-recycled-2m',49.0),
        ('USB-C Cable 1m - 100% Recycled Copper Edition','usbc-recycled-1m',19.0),
        ('USB-C Cable 2m - 100% Recycled Copper Edition','usbc-recycled-2m',29.0),
        ('Apple Pencil USB-C - Recycled Aluminum',   'pencil-usbc-recycled', 79.0),
        ('iPad Smart Folio Bag - Hemp Outer',         'smart-folio-hemp-bag', 89.0),
        ('Travel Adapter - Recycled Plastic Core',    'travel-adapter-recycled',39.0),
        ('AirTag - Recycled Tin Engraving Pack',      'airtag-recycled-tin', 29.0),
    ]
    for name, slug_suffix, price in sustain_skus:
        slug = f'sustain-r5-{slug_suffix}'
        specs = _r5_deepen({'kind': 'Sustainability', 'recycled_content_pct': 100,
                            'apple_environmental_responsibility_report': 'Apple 2025 Environmental Progress Report'},
                           env='100% recycled materials in primary components. Apple Carbon Neutral product line. '
                             'Final assembly uses 100% renewable electricity. Apple Carbon Removal portfolio offsets remaining emissions.',
                           a11y=['Tactile recycled-content engraving aids identification'],
                           in_box=['Item', 'Sustainability info card', 'Recyclable mailer'],
                           whats_new='R5 — Joins the Apple 2030 carbon-neutral product line. Includes detailed environment report card.')
        extra.append((name, slug, 'accessories', 'sustainability',
                      f'{name}. Made with 100% recycled materials.',
                      f'{name}. Apple 2030 carbon-neutral product. Made with 100% recycled materials in primary components. '
                      f'Final assembly uses 100% renewable electricity.', price, None, ['Recycled'], [], specs, 2026, ''))

    # ------------------------------------------------------------------
    # J. Today-at-Apple themed session kits.
    # ------------------------------------------------------------------
    today_kits = [
        ('Today at Apple - Photo Walk Kit',         'today-photo-walk',         0.0,    'Photo walk kit — sample shooting prompts and a Today at Apple lens guide.'),
        ('Today at Apple - Sketch with Procreate',  'today-procreate',          0.0,    'Procreate session kit — brush packs and Apple Pencil tips card.'),
        ('Today at Apple - Watch Walking Club Pack','today-walking-club',       0.0,    'Walking club kit — heart-rate goal cards and route guides.'),
        ('Today at Apple - Music Lab Live Loops',   'today-music-lab',          0.0,    'Music lab live loops — Logic Pro Live Loops grids and a session songbook.'),
        ('Today at Apple - Final Cut Pro for iPad', 'today-fcp-ipad',           0.0,    'Final Cut Pro for iPad session — sample timelines and a creator guide.'),
        ('Today at Apple - Coding with Swift',      'today-swift',              0.0,    'Coding with Swift kit — Swift Playgrounds book and a teacher guide.'),
        ('Today at Apple - Art with iPad',          'today-art-ipad',           0.0,    'Art with iPad kit — color theory book and Apple Pencil pressure card.'),
        ('Today at Apple - Photo Lab (Lightroom)',  'today-photo-lab',          0.0,    'Photo Lab kit — Lightroom presets card and an exposure cheat sheet.'),
        ('Today at Apple - AirPods Pro Studio',     'today-airpods-studio',     0.0,    'AirPods Pro Studio session — Adaptive Audio walkthroughs and a Hearing Aid feature card.'),
        ('Today at Apple - Vision Pro Spatial',     'today-vision-spatial',     0.0,    'Vision Pro Spatial session — Spatial Video shooting card and a Personas setup walkthrough.'),
        ('Today at Apple - Apple Card Workshop',    'today-apple-card',         0.0,    'Apple Card workshop — Daily Cash optimization and Apple Wallet hotel keys overview.'),
        ('Today at Apple - Family Sharing Setup',   'today-family-sharing',     0.0,    'Family Sharing setup — Ask to Buy walkthrough and a Find My Family setup card.'),
        ('Today at Apple - Music Theory iPad',      'today-music-theory',       0.0,    'Music theory on iPad — Garageband lesson plan and a chord wheel card.'),
        ('Today at Apple - Apple Watch Fitness',    'today-watch-fitness',      0.0,    'Apple Watch Fitness — Vitals app card and a 28-day Fitness+ trial code.'),
        ('Today at Apple - Memoji & Animoji',       'today-memoji',             0.0,    'Memoji session — sticker pack card and an iMessage flow guide.'),
    ]
    for name, slug_suffix, price, desc in today_kits:
        slug = f'today-r5-{slug_suffix}'
        specs = _r5_deepen({'kind': 'Today at Apple Kit', 'audience': 'Workshop attendees'},
                           env='Printed on FSC-certified recycled paper with soy-based inks.',
                           a11y=['Large-print booklets available', 'ASL interpretation on request',
                                 'Captioned demo videos via QR code'],
                           in_box=['Session card', 'Sample assets', 'QR code to companion app'],
                           whats_new='R5 — Adds Apple Intelligence demos in the Vision Pro, Photo, and Sketch tracks.')
        extra.append((name, slug, 'accessories', 'today-at-apple',
                      f'{name}. Today at Apple session companion.',
                      desc, price, None, ['Workshop'], [], specs, 2026, ''))

    # ------------------------------------------------------------------
    # K. iPhone screen protector + cleaning kit deep-spec matrix.
    # ------------------------------------------------------------------
    cleaning_skus = [
        ('Polishing Cloth (R5)',         'polishing-cloth-r5',         19.0, 'Polishing cloth for Apple displays.'),
        ('Polishing Cloth Pro Pack (3)', 'polishing-cloth-3pk',        49.0, '3-pack polishing cloths for Apple displays.'),
        ('Polishing Cloth (XL, Studio)', 'polishing-cloth-xl',         29.0, 'XL polishing cloth — sized for Studio Display and Pro Display XDR.'),
        ('Display Cleaning Kit',         'display-cleaning-kit',       29.0, 'Display cleaning kit — display-safe spray and microfiber cloth.'),
        ('Mac Keyboard Cleaning Pack',   'mac-keyboard-cleaning',      29.0, 'Mac keyboard cleaning pack — keycap puller, compressed air, and microfiber.'),
        ('AirPods Cleaning Kit',         'airpods-cleaning-kit',       19.0, 'AirPods cleaning kit — earwax brushes and tip-cleaning swabs.'),
        ('iPhone Camera Lens Cleaning',  'iphone-camera-cleaning',     19.0, 'iPhone camera lens cleaning kit — fluid and lint-free swabs.'),
        ('Vision Pro Polishing Pen',     'vision-polishing-pen',       19.0, 'Vision Pro polishing pen — for precision cleaning of the front lens.'),
        ('Apple Watch Strap Cleaning',   'watch-strap-cleaning',       19.0, 'Apple Watch strap cleaning kit — gentle saddle soap for leather bands.'),
        ('Studio Display Polishing Bundle','studio-display-bundle',    39.0, 'Studio Display polishing bundle — XL cloth, fluid, and microfiber gloves.'),
    ]
    for name, slug_suffix, price, desc in cleaning_skus:
        slug = f'clean-r5-{slug_suffix}'
        specs = _r5_deepen({'kind': 'Cleaning', 'safe_for': 'Apple displays and devices'},
                           env='Cloths made from 65% recycled microfiber; cleaning fluid is alcohol-free and biodegradable.',
                           a11y=['VoiceOver friendly packaging with raised label'],
                           in_box=['Item', 'Usage card'],
                           whats_new='R5 — Adds Vision Pro polishing pen and Studio Display XL bundle.')
        extra.append((name, slug, 'accessories', 'cleaning',
                      f'{name}. Safe for Apple displays.',
                      desc, price, None, ['Default'], [], specs, 2026, ''))

    # ------------------------------------------------------------------
    # L. Internationalized travel adapter kits + region-specific power.
    # ------------------------------------------------------------------
    travel_regions = [
        ('Europe', 'eu', 'Type C/E/F'),
        ('UK', 'uk', 'Type G'),
        ('Australia', 'au', 'Type I'),
        ('Japan', 'jp', 'Type A'),
        ('Korea', 'kr', 'Type C/F'),
        ('India', 'in', 'Type C/D/M'),
        ('Brazil', 'br', 'Type N'),
        ('China', 'cn', 'Type A/I'),
        ('Argentina', 'ar', 'Type C/I'),
        ('Switzerland', 'ch', 'Type J'),
        ('Italy', 'it', 'Type L'),
        ('South Africa', 'za', 'Type M'),
    ]
    for region_name, region_slug, plug_type in travel_regions:
        for watts in [20, 30, 67, 96]:
            slug = f'travel-r5-{region_slug}-{watts}w'
            name = f'{watts}W USB-C Power Adapter — {region_name} Plug ({plug_type})'
            specs = _r5_deepen({'watts': watts, 'region': region_name, 'plug_type': plug_type},
                               env='Made with 92% post-consumer recycled plastic in the enclosure. '
                                 'Final assembly uses 100% renewable electricity.',
                               a11y=['VoiceOver-friendly tactile USB-C orientation notch'],
                               in_box=[f'{watts}W USB-C Power Adapter ({region_name} plug)', 'Documentation'],
                               whats_new='R5 — Adds GaN-based circuitry for smaller form factor.')
            extra.append((name, slug, 'accessories', 'charger',
                          f'{name}. Region-specific plug.',
                          f'{name}. USB-C charger optimized for {region_name} outlets. {watts}W output. '
                          f'Compatible with iPhone, iPad, MacBook Air, and AirPods.',
                          float(30 + watts), None, ['White'], [], specs, 2026, ''))

    # ------------------------------------------------------------------
    # M. Mac Pro tower + Mac Studio Ultra configurations.
    # ------------------------------------------------------------------
    mac_pro_skus = [
        ('Mac Pro M2 Ultra (Tower)',    'mac-pro-m2-ultra-tower',    6999.0, 'M2 Ultra', '64GB',  '1TB'),
        ('Mac Pro M2 Ultra (Rack)',     'mac-pro-m2-ultra-rack',     7499.0, 'M2 Ultra', '64GB',  '1TB'),
        ('Mac Pro M2 Ultra 192GB (Tower)','mac-pro-m2-ultra-192gb-tower',8799.0,'M2 Ultra','192GB','2TB'),
        ('Mac Pro M2 Ultra 8TB (Tower)','mac-pro-m2-ultra-8tb-tower',10999.0,'M2 Ultra','192GB','8TB'),
        ('Mac Studio M2 Max',           'mac-studio-r5-m2-max',     1999.0, 'M2 Max',  '32GB',  '512GB'),
        ('Mac Studio M2 Ultra',         'mac-studio-r5-m2-ultra',   3999.0, 'M2 Ultra','64GB',  '1TB'),
        ('Mac Studio M2 Ultra 192GB',   'mac-studio-r5-m2-ultra-192gb',5599.0,'M2 Ultra','192GB','2TB'),
        ('Mac Studio M4 Max',           'mac-studio-r5-m4-max',     1999.0, 'M4 Max',  '36GB',  '512GB'),
        ('Mac Studio M4 Ultra',         'mac-studio-r5-m4-ultra',   3999.0, 'M4 Ultra','64GB',  '1TB'),
        ('Mac Studio M4 Ultra 256GB',   'mac-studio-r5-m4-ultra-256gb',7299.0,'M4 Ultra','256GB','2TB'),
    ]
    for name, slug, price, chip, mem, storage in mac_pro_skus:
        full_slug = f'mac-r5-{slug}'
        specs = _r5_deepen({
            'chip': chip, 'memory': mem, 'storage': storage,
            'cooling': 'Aluminum thermal substructure', 'i_o': 'Thunderbolt 4 × 8, HDMI 2.1, 10Gb Ethernet',
        }, env='Made with 100% recycled aluminum, 100% recycled rare earth elements, and 100% renewable energy for final assembly. '
             'Apple Environmental Progress Report 2025.',
           a11y=['VoiceOver', 'macOS Accessibility Shortcut', 'Dwell Control', 'Voice Control', 'Switch Control'],
           in_box=[name, 'Power cord', 'Documentation'],
           whats_new='R5 — Adds Apple Intelligence on-device LLM and ProRes engine for 8K editing.')
        extra.append((name, full_slug, 'mac', 'mac-pro',
                      f'{name}. Workstation power.',
                      f'{name}. Apple silicon workstation with {chip} chip, {mem} unified memory, and {storage} SSD. '
                      f'Built for ProRes editing and ML training workflows.',
                      price, round(price/24, 2), ['Silver'], [storage], specs, 2024, chip))

    # ------------------------------------------------------------------
    # N. iPhone Pro carrier-locked / unlocked / dual-SIM variants.
    # ------------------------------------------------------------------
    carriers = ['AT&T', 'Verizon', 'T-Mobile', 'Unlocked', 'Dual-SIM Unlocked']
    for model, model_slug, base_price in [
        ('iPhone 17', 'iphone-17', 799.0),
        ('iPhone 17 Pro', 'iphone-17-pro', 1099.0),
        ('iPhone 17 Pro Max', 'iphone-17-pro-max', 1199.0),
        ('iPhone Air', 'iphone-air', 999.0),
        ('iPhone 17e', 'iphone-17e', 599.0),
    ]:
        for carrier in carriers:
            carrier_slug = carrier.lower().replace('&', 'and').replace(' ', '-').replace('-', '-')
            slug = f'iphone-r5-{model_slug}-{carrier_slug}'
            name = f'{model} - {carrier}'
            specs = _r5_deepen({'carrier': carrier, 'lock_status': 'Unlocked' if 'Unlocked' in carrier else 'Locked'},
                               env='Made with 95%+ recycled rare earth elements and 100% recycled cobalt in the battery.',
                               a11y=['VoiceOver', 'Dynamic Type', 'Made for iPhone hearing aids'],
                               in_box=[model, 'USB-C Charge Cable (1 m)', 'Documentation'],
                               whats_new=f'R5 — Adds carrier-managed Apple Wallet activation for {carrier}.')
            extra.append((name, slug, 'iphone', 'iphone-carrier',
                          f'{name}. {carrier}.',
                          f'{name}. Configured for {carrier}. Same hardware as the standard model with carrier-managed activation.',
                          base_price, round(base_price/24, 2), ['Black'], ['128GB'], specs, 2025, 'A19 Pro'))

    # ------------------------------------------------------------------
    # O. AirPods cases (color matrix + Hermès / Pride / Unity).
    # ------------------------------------------------------------------
    airpods_cases = [
        ('AirPods Pro Smart Case - Midnight', 'airpods-pro-case-midnight', 39.0),
        ('AirPods Pro Smart Case - Starlight', 'airpods-pro-case-starlight', 39.0),
        ('AirPods Pro Smart Case - Sky', 'airpods-pro-case-sky', 39.0),
        ('AirPods Pro Smart Case - Forest', 'airpods-pro-case-forest', 39.0),
        ('AirPods Pro Smart Case - Sand', 'airpods-pro-case-sand', 39.0),
        ('AirPods Pro Hermès Case - Bridge', 'airpods-pro-hermes-bridge', 199.0),
        ('AirPods Pro Hermès Case - Saddle', 'airpods-pro-hermes-saddle', 199.0),
        ('AirPods Pro Pride Edition Case', 'airpods-pro-pride', 49.0),
        ('AirPods Pro Unity Edition Case', 'airpods-pro-unity', 49.0),
        ('AirPods Max Smart Case - Midnight', 'airpods-max-case-midnight', 59.0),
        ('AirPods Max Smart Case - Starlight', 'airpods-max-case-starlight', 59.0),
        ('AirPods 4 Carry Case - Black', 'airpods-4-case-black', 29.0),
        ('AirPods 4 Carry Case - Blue', 'airpods-4-case-blue', 29.0),
        ('AirPods 4 Carry Case - Pink', 'airpods-4-case-pink', 29.0),
        ('AirPods Pro Lanyard - Black', 'airpods-pro-lanyard-black', 19.0),
        ('AirPods Pro Lanyard - Pride', 'airpods-pro-lanyard-pride', 19.0),
        ('AirPods Pro Lanyard - Pacific Blue', 'airpods-pro-lanyard-pacific', 19.0),
        ('AirPods Pro Hook (Apple Watch Strap)', 'airpods-pro-hook-watch', 29.0),
        ('AirPods Pro Magnetic Stand', 'airpods-pro-magnetic-stand', 49.0),
        ('AirPods Pro Travel Pouch', 'airpods-pro-travel-pouch', 39.0),
    ]
    for name, slug_suffix, price in airpods_cases:
        slug = f'airpods-r5-{slug_suffix}'
        specs = _r5_deepen({'kind': 'AirPods Case', 'compat': 'AirPods Pro / Max / 4'},
                           env='Made with 100% recycled silicone outer layer. Hermès variants use vegetable-tanned leather.',
                           a11y=['Tactile orientation notch aids one-hand opening'],
                           in_box=['Item'],
                           whats_new='R5 — Adds Find My-enabled tracking and U2 chip for Precision Finding.')
        extra.append((name, slug, 'accessories', 'airpods-case',
                      f'{name}. Designed by Apple.',
                      f'{name}. Find My enabled. MagSafe-compatible attach points. U2 chip for Precision Finding from iPhone.',
                      price, None, ['Default'], [], specs, 2026, ''))

    # ------------------------------------------------------------------
    # P. iPad Magic Keyboard expanded colors (R5).
    # ------------------------------------------------------------------
    mk_colors_r5 = ['Black', 'White', 'Charcoal Gray', 'Light Violet', 'Denim', 'Sage', 'Marigold',
                    'Storm Blue', 'Cypress', 'Sun Yellow']
    for model, model_slug, base_price in [
        ('iPad Pro 11" M4', 'ipad-pro-11-m4', 299.0),
        ('iPad Pro 13" M4', 'ipad-pro-13-m4', 349.0),
        ('iPad Air 11" M4', 'ipad-air-11-m4', 269.0),
        ('iPad Air 13" M4', 'ipad-air-13-m4', 319.0),
    ]:
        for c in mk_colors_r5:
            slug = f'mk-r5-{model_slug}-{c.lower().replace(" ", "-")}'
            name = f'Magic Keyboard for {model} - {c} (R5)'
            specs = _r5_deepen({'compat': model, 'color': c, 'kind': 'Magic Keyboard'},
                               env='Made with 75% recycled aluminum in the keyboard chassis and 100% recycled rare earth magnets.',
                               a11y=['Backlit keys with Dynamic Type-sized labels', 'VoiceOver-friendly tactile dot on F/J keys',
                                     'Trackpad supports VoiceOver and AssistiveTouch gestures'],
                               in_box=['Magic Keyboard', 'USB-C passthrough port', 'Documentation'],
                               whats_new='R5 — Adds function key row, glass trackpad, and aluminum palm rest.')
            extra.append((name, slug, 'accessories', 'ipad-keyboard',
                          f'{name}. Floating cantilever design.',
                          f'{name}. Backlit keys, full-size function row, glass trackpad, and USB-C passthrough charging.',
                          base_price, None, [c], [], specs, 2025, ''))

    # ------------------------------------------------------------------
    # Q. iPad pencil + accessory matrix expansion.
    # ------------------------------------------------------------------
    pencil_skus = [
        ('Apple Pencil Pro Tips (4pk) - R5',  'pencil-pro-tips-4pk-r5',  19.0),
        ('Apple Pencil Pro Tips (10pk) - R5', 'pencil-pro-tips-10pk-r5', 39.0),
        ('Apple Pencil USB-C Tips (4pk) - R5','pencil-usbc-tips-4pk-r5', 15.0),
        ('Apple Pencil USB-C Tips (10pk) - R5','pencil-usbc-tips-10pk-r5',29.0),
        ('Apple Pencil Holder for iPad Pro',  'pencil-holder-pro-r5',    19.0),
        ('Apple Pencil Holder for iPad Air',  'pencil-holder-air-r5',    19.0),
        ('Apple Pencil Magnetic Stand',       'pencil-magnetic-stand-r5',29.0),
        ('Apple Pencil Engraving Pack',       'pencil-engraving-pack-r5', 9.0),
        ('Apple Pencil Pro - Engraved Edition (Initials)','pencil-pro-engraved-r5',129.0),
        ('Apple Pencil USB-C - Engraved Edition (Initials)','pencil-usbc-engraved-r5',79.0),
        ('Apple Pencil Travel Case (Single)', 'pencil-travel-case-single-r5',29.0),
        ('Apple Pencil Travel Case (Multi)',  'pencil-travel-case-multi-r5',49.0),
        ('Apple Pencil USB-C Charger Cap (3pk)','pencil-usbc-charger-cap-r5',9.0),
        ('Apple Pencil Cleaning Kit',         'pencil-cleaning-kit-r5',  19.0),
        ('Apple Pencil Ergonomic Grip (Set)', 'pencil-grip-set-r5',      29.0),
    ]
    for name, slug_suffix, price in pencil_skus:
        slug = f'pencil-r5-{slug_suffix}'
        specs = _r5_deepen({'kind': 'Apple Pencil Accessory'},
                           env='Made with 70%+ recycled plastic in the tips and recycled aluminum in holders.',
                           a11y=['Tactile orientation aids one-hand orientation'],
                           in_box=['Item'],
                           whats_new='R5 — Adds Find My pairing for Apple Pencil Pro and Engraving via Wallet.')
        extra.append((name, slug, 'accessories', 'apple-pencil',
                      f'{name}. Designed for Apple Pencil.',
                      f'{name}. Compatible with Apple Pencil Pro and Apple Pencil (USB-C). Find My-enabled where applicable.',
                      price, None, ['Default'], [], specs, 2026, ''))

    # ------------------------------------------------------------------
    # R. Repair-status / self-service repair SKUs.
    # ------------------------------------------------------------------
    repair_skus = [
        ('iPhone Battery Service Kit (Self Service Repair)',  'iphone-battery-kit',  69.0),
        ('iPhone Display Service Kit (Self Service Repair)',  'iphone-display-kit', 269.0),
        ('iPhone Camera Service Kit (Self Service Repair)',   'iphone-camera-kit',  129.0),
        ('iPhone Bottom Speaker Kit (Self Service Repair)',   'iphone-speaker-kit',  29.0),
        ('iPhone Taptic Engine Kit (Self Service Repair)',    'iphone-taptic-kit',   39.0),
        ('iPhone SIM Tray Kit (Self Service Repair)',         'iphone-sim-kit',      19.0),
        ('Mac Battery Service Kit (Self Service Repair)',     'mac-battery-kit',    129.0),
        ('Mac Top Case Kit (Self Service Repair)',            'mac-top-case-kit',   199.0),
        ('Mac Keyboard Kit (Self Service Repair)',            'mac-keyboard-kit',    99.0),
        ('Mac Trackpad Kit (Self Service Repair)',            'mac-trackpad-kit',    89.0),
        ('iPad Battery Service Kit (Self Service Repair)',    'ipad-battery-kit',    99.0),
        ('Watch Battery Service Kit (Self Service Repair)',   'watch-battery-kit',   59.0),
        ('Self Service Repair Toolkit (1-week loaner)',       'repair-toolkit-loaner', 49.0),
        ('Self Service Repair Heated Pad',                    'repair-heated-pad',    99.0),
        ('Self Service Repair Display Press',                 'repair-display-press',129.0),
        ('Self Service Repair Pentalobe Set',                 'repair-pentalobe-set',  29.0),
        ('Self Service Repair Torque Driver',                 'repair-torque-driver',  79.0),
        ('Self Service Repair Suction Cup',                   'repair-suction-cup',    19.0),
        ('Self Service Repair Adhesive Strip Pack',           'repair-adhesive-pack',  19.0),
        ('Self Service Repair Cleaning Wipes',                'repair-cleaning-wipes', 9.0),
    ]
    for name, slug_suffix, price in repair_skus:
        slug = f'repair-r5-{slug_suffix}'
        specs = _r5_deepen({'kind': 'Self Service Repair', 'service_class': 'Apple-authorized parts'},
                           env='Parts manufactured to Apple Genuine specifications. Postage-paid recycling mailer included.',
                           a11y=['Repair manuals support VoiceOver and Dynamic Type'],
                           in_box=['Part', 'Repair manual QR card', 'Recycling mailer'],
                           whats_new='R5 — Adds /repair/status tracking, IMEI / serial validation, and chat-with-Apple-Specialist routing.')
        extra.append((name, slug, 'accessories', 'self-service-repair',
                      f'{name}. Apple Self Service Repair.',
                      f'{name}. Apple Self Service Repair part. Includes step-by-step instructions and a postage-paid mailer for the old part. '
                      f'Track your repair status at /repair/status with your repair number.',
                      price, None, ['Default'], [], specs, 2026, ''))

    # ------------------------------------------------------------------
    # S. Beats colors expansion (Studio Pro, Solo 4, Pill, Fit Pro).
    # ------------------------------------------------------------------
    beats_skus = [
        ('Beats Studio Pro - Cosmic Silver R5',  'beats-studio-cosmic-silver-r5', 349.99),
        ('Beats Studio Pro - Sandstone R5',      'beats-studio-sandstone-r5',     349.99),
        ('Beats Studio Pro - Navy R5',           'beats-studio-navy-r5',          349.99),
        ('Beats Studio Pro - Pacific Blue R5',   'beats-studio-pacific-blue-r5',  349.99),
        ('Beats Studio Pro - Cinnamon R5',       'beats-studio-cinnamon-r5',      349.99),
        ('Beats Solo 4 - Matte Black R5',        'beats-solo-4-matte-black-r5',   199.99),
        ('Beats Solo 4 - Cloud Pink R5',         'beats-solo-4-cloud-pink-r5',    199.99),
        ('Beats Solo 4 - Slate Blue R5',         'beats-solo-4-slate-blue-r5',    199.99),
        ('Beats Solo 4 - Forest Green R5',       'beats-solo-4-forest-r5',        199.99),
        ('Beats Solo 4 - Sand Dune R5',          'beats-solo-4-sand-r5',          199.99),
        ('Beats Pill - Statement Red R5',        'beats-pill-statement-red-r5',   149.99),
        ('Beats Pill - Matte Black R5',          'beats-pill-matte-black-r5',     149.99),
        ('Beats Pill - Champagne Gold R5',       'beats-pill-champagne-r5',       149.99),
        ('Beats Pill - Pacific Blue R5',         'beats-pill-pacific-blue-r5',    149.99),
        ('Beats Fit Pro - Volt Yellow R5',       'beats-fit-pro-volt-yellow-r5',  199.99),
        ('Beats Fit Pro - Tidal Blue R5',        'beats-fit-pro-tidal-blue-r5',   199.99),
        ('Beats Fit Pro - Coral Pink R5',        'beats-fit-pro-coral-pink-r5',   199.99),
        ('Beats Powerbeats Pro - Sport Yellow R5','beats-pbp-sport-yellow-r5',    249.99),
        ('Beats Powerbeats Pro - Bone White R5', 'beats-pbp-bone-white-r5',       249.99),
        ('Beats Powerbeats Pro - Spring Yellow R5','beats-pbp-spring-yellow-r5',  249.99),
    ]
    for name, slug, price in beats_skus:
        full_slug = f'beats-r5-{slug}'
        specs = _r5_deepen({'kind': 'Beats', 'chip': 'H2', 'anc': 'Active Noise Cancellation'},
                           env='Made with 60%+ recycled plastic in housings and recycled aluminum in audio hinges.',
                           a11y=['Spatial Audio with Dynamic Head Tracking', 'Live Listen (with iPhone)', 'Hearing Aid feature pairing'],
                           in_box=['Beats device', 'USB-C charging cable', 'Quick start guide'],
                           whats_new='R5 — Adds iCloud-synced EQ presets and Find My network locate.')
        extra.append((name, full_slug, 'audio', 'beats',
                      f'{name}. Beats sound.',
                      f'{name}. Apple H2 chip. Spatial Audio. Find My-enabled. iCloud-synced EQ.',
                      price, None, ['Default'], [], specs, 2026, 'H2'))

    # ------------------------------------------------------------------
    # T. iPhone bundle gift packs (R5 finale).
    # ------------------------------------------------------------------
    bundle_skus = [
        ('iPhone 17 Pro Starter Bundle',        'iphone-17-pro-starter',        1299.0,
         'iPhone 17 Pro + AppleCare+ 1 year + MagSafe Charger 1m + Silicone Case.'),
        ('iPhone 17 Pro Max Photographer Pack', 'iphone-17-pro-max-photo',      1499.0,
         'iPhone 17 Pro Max + Moment Lens Mount + ND Filter Kit + Final Cut Camera Pro Kit.'),
        ('iPhone Air Travel Pack',              'iphone-air-travel',             1199.0,
         'iPhone Air + World Travel Adapter Kit + USB-C Cable 2m + AirTag.'),
        ('iPhone 17 Family Bundle',             'iphone-17-family',              1899.0,
         '2× iPhone 17 + Family Sharing kit + AirTag 4-pack + Apple One Family 6 months.'),
        ('Back to School Mac Bundle',           'mac-back-to-school',            1599.0,
         'MacBook Air 13" + AirPods 4 + AppleCare+ Education + Pro Apps for Education bundle.'),
        ('Creator iPad Pro Bundle',             'ipad-pro-creator',              2199.0,
         'iPad Pro 13" M4 + Apple Pencil Pro + Magic Keyboard + Final Cut Pro for iPad.'),
        ('Apple Watch Ultra 3 Adventure Pack',  'watch-ultra-adventure',         999.0,
         'Apple Watch Ultra 3 + Alpine Loop + Ocean Band + Apple Fitness+ 12 months.'),
        ('HomeKit Starter Bundle',              'homekit-starter',                399.0,
         'HomePod mini + Apple TV 4K + Eve Energy Smart Plug + Philips Hue Bridge.'),
        ('Vision Pro Cinema Bundle',            'vision-cinema',                 3999.0,
         'Apple Vision Pro 512GB + AppleCare+ + Travel Case + ZEISS Optical Inserts (Readers).'),
        ('Apple Card Welcome Bundle',           'apple-card-welcome',              99.0,
         'Apple Card welcome materials + titanium card sleeve + cleaning cloth + Apple Pay setup card.'),
    ]
    for name, slug_suffix, price, desc in bundle_skus:
        slug = f'bundle-r5-{slug_suffix}'
        specs = _r5_deepen({'kind': 'Bundle', 'bundle_savings_usd': round(price * 0.08, 2)},
                           env='Bundles ship in a single recyclable mailer. Final assembly uses 100% renewable electricity.',
                           a11y=['VoiceOver setup card walks through each device in the bundle'],
                           in_box=['Each bundled product', 'Setup guide', 'AppleCare+ enrollment card (where applicable)'],
                           whats_new='R5 — Adds one-tap Apple Wallet activation across every bundled device.')
        extra.append((name, slug, 'accessories', 'bundle',
                      f'{name}. Save when you bundle.',
                      desc, price, round(price/24, 2), ['Bundle'], [], specs, 2026, ''))

    # ------------------------------------------------------------------
    # U. Apple Watch faces and complications — digital downloads.
    # ------------------------------------------------------------------
    watch_face_skus = [
        ('Apple Watch Face — Snoopy',           'face-snoopy',        0.0),
        ('Apple Watch Face — Astronomy',        'face-astronomy',     0.0),
        ('Apple Watch Face — Solar Graph',      'face-solar-graph',   0.0),
        ('Apple Watch Face — Unity Bloom',      'face-unity-bloom',   0.0),
        ('Apple Watch Face — Black Unity',      'face-black-unity',   0.0),
        ('Apple Watch Face — Pride Threads',    'face-pride-threads', 0.0),
        ('Apple Watch Face — International Womens Day','face-iwd',    0.0),
        ('Apple Watch Face — Lunar New Year',   'face-lunar-new-year',0.0),
        ('Apple Watch Face — Numerals Duo',     'face-numerals-duo',  0.0),
        ('Apple Watch Face — Modular Ultra',    'face-modular-ultra', 0.0),
        ('Apple Watch Face — Wayfinder',        'face-wayfinder',     0.0),
        ('Apple Watch Face — Photos Always On', 'face-photos-ao',     0.0),
        ('Apple Watch Face — Memoji Always On', 'face-memoji-ao',     0.0),
        ('Apple Watch Face — Stripes',          'face-stripes',       0.0),
        ('Apple Watch Face — Toy Story',        'face-toy-story',     0.0),
    ]
    for name, slug_suffix, price in watch_face_skus:
        slug = f'face-r5-{slug_suffix}'
        specs = _r5_deepen({'kind': 'Watch Face', 'compat': 'Apple Watch'},
                           env='Digital download — no packaging.',
                           a11y=['VoiceOver friendly', 'Reduce Motion compatible'],
                           in_box=['Watch face download link'],
                           whats_new='R5 — New Photos Always On and Memoji Always On faces for Apple Watch.')
        extra.append((name, slug, 'accessories', 'watch-face',
                      f'{name}. Free watch face.',
                      f'{name} for Apple Watch. Free digital download. Customize complications and color palette.',
                      price, None, ['Watch'], [], specs, 2026, ''))

    # ------------------------------------------------------------------
    # V. iPhone Pro display sticker / engraving customization.
    # ------------------------------------------------------------------
    engraving_skus = [
        ('iPhone Engraving — Emoji (paid pack)', 'engraving-emoji-pack', 0.0),
        ('iPhone Engraving — Text only',         'engraving-text-only',  0.0),
        ('iPhone Engraving — Mixed text + emoji','engraving-mixed',      0.0),
        ('AirPods Engraving — Text only',        'engraving-airpods-text',0.0),
        ('AirPods Engraving — Emoji',            'engraving-airpods-emoji',0.0),
        ('iPad Engraving — Text only',           'engraving-ipad-text',  0.0),
        ('Apple Pencil Engraving — Text',        'engraving-pencil-text',0.0),
        ('AirTag Engraving — Text + Emoji',      'engraving-airtag-mixed',0.0),
        ('Apple Watch Cellular ID Engraving',    'engraving-watch-id',   0.0),
        ('Beats Engraving — Text only',          'engraving-beats-text', 0.0),
    ]
    for name, slug_suffix, price in engraving_skus:
        slug = f'engrave-r5-{slug_suffix}'
        specs = _r5_deepen({'kind': 'Engraving Service'},
                           env='Engraving uses laser etching — no chemicals, no additional packaging.',
                           a11y=['Tactile engraving aids identification for low-vision users'],
                           in_box=['Standard product packaging with engraved item'],
                           whats_new='R5 — Mixed text + emoji engravings now available in 35 languages.')
        extra.append((name, slug, 'accessories', 'engraving',
                      f'{name}. Free engraving.',
                      f'{name}. Personalize your Apple device with free engraving. Mixed text and emoji supported on iPhone, iPad, AirTag, and AirPods.',
                      price, None, ['Engraving'], [], specs, 2026, ''))

    # ------------------------------------------------------------------
    # W. AppleCare+ for Business / Enterprise tier.
    # ------------------------------------------------------------------
    business_care = [
        ('AppleCare+ for Business — iPhone (per device)',   'biz-iphone',   18.99, 'iPhone'),
        ('AppleCare+ for Business — iPad (per device)',     'biz-ipad',     12.99, 'iPad'),
        ('AppleCare+ for Business — MacBook (per device)',  'biz-mac',      32.99, 'MacBook'),
        ('AppleCare+ for Business — Apple Watch (per device)','biz-watch',   6.99, 'Apple Watch'),
        ('AppleCare+ for Business — Apple TV (per device)', 'biz-tv',        4.99, 'Apple TV'),
        ('AppleCare+ for Business — Vision Pro (per device)','biz-vision',  44.99, 'Vision Pro'),
        ('AppleCare Professional Support — Mac admin',      'pro-mac',      999.0, 'Mac admin'),
        ('AppleCare Professional Support — Server (year)',  'pro-server',  2499.0, 'Server'),
        ('AppleCare for Enterprise — Tier 1 (year)',        'enterprise-1',2999.0, 'Enterprise'),
        ('AppleCare for Enterprise — Tier 2 (year)',        'enterprise-2',5999.0, 'Enterprise'),
        ('AppleCare for Enterprise — Tier 3 (year)',        'enterprise-3',9999.0, 'Enterprise'),
        ('AppleCare Onsite Service — Education site (year)','onsite-edu',  4999.0, 'Education'),
        ('AppleCare Onsite Service — Business site (year)', 'onsite-biz',  6999.0, 'Business'),
        ('AppleCare AOS Tools (Apple-trained tech)',        'aos-tools',    999.0, 'AOS'),
        ('Apple Business Manager Onboarding (per seat)',    'abm-onboard',   29.0, 'ABM'),
    ]
    for name, slug_suffix, price, target in business_care:
        slug = f'biz-r5-{slug_suffix}'
        specs = _r5_deepen({'kind': 'AppleCare for Business', 'target': target,
                            'audience': 'Business / Enterprise / Education'},
                           env='Service shipping uses carbon-neutral logistics. Service documentation digital-only.',
                           a11y=['Service appointments accept VoiceOver bookings'],
                           in_box=['Coverage certificate (digital)', 'Enterprise onboarding guide'],
                           whats_new='R5 — Adds AppleCare Coverage Lookup API + serial-bulk import in Apple Business Manager.')
        extra.append((name, slug, 'accessories', 'business-care',
                      f'{name}. Apple Business Essentials add-on.',
                      f'{name}. Designed for fleet device management. Bulk service entitlement, single-invoice billing, '
                      f'and Apple-trained-specialist routing. Pair with Apple Business Manager for zero-touch onboarding.',
                      price, None, ['Business'], [], specs, 2026, ''))

    return extra


EXTRA_PRODUCTS_R5 = _extend_r5()


# ===========================================================================
# R6 expansion — 600+ additional SKUs covering iPhone 17 case colorways,
# Apple Watch band colorways, HomeKit accessories, gift-card denominations,
# refurbished SKUs, AppleCare bundles, sustainability + pencil/keyboard line.
# Procedurally generated for deterministic seed-byte identity.
# ===========================================================================

def _r6_specs(base, env=None, a11y=None, in_box=None, whats_new=None,
              compatibility=None, breadcrumb=None):
    out = dict(base) if base else {}
    if env:           out['environment_report'] = env
    if a11y:          out['accessibility_features'] = a11y
    if in_box:        out['in_box'] = in_box
    if whats_new:     out['whats_new'] = whats_new
    if compatibility: out['compatibility'] = compatibility
    if breadcrumb:    out['breadcrumb_hint'] = breadcrumb
    return out


def _extend_r6():
    """R6 — generate ~620 SKUs across 8 deterministic batches."""
    extra = []

    # A. iPhone 17 case colorways — 7 styles × 8 colors × 4 models = 224 SKUs
    iphone_17_models = [
        ('iPhone 17',         'iphone-17',         '17'),
        ('iPhone 17 Pro',     'iphone-17-pro',     '17-pro'),
        ('iPhone 17 Pro Max', 'iphone-17-pro-max', '17-pro-max'),
        ('iPhone Air',        'iphone-air',        'air'),
    ]
    iphone_17_colors = ['Cypress','Lake Green','Sunset Orange','Plum Purple',
                        'Indigo Sky','Sandstone','Black','Stone Gray']
    case_styles = [
        ('Silicone Case (R6)',   'silicone-r6',   49.0, 'Premium silicone with soft microfiber lining.'),
        ('Clear Case (R6)',      'clear-r6',      49.0, 'Crystal-clear polycarbonate that shows off iPhone color.'),
        ('FineWoven Case (R6)',  'finewoven-r6',  59.0, 'Recycled twill weave with rich texture and feel.'),
        ('Beats Case (R6)',      'beats-r6',      69.0, 'Beats x Apple co-design case with shock-absorbent edges.'),
        ('Crossbody Case (R6)',  'crossbody-r6',  79.0, 'Magnetic case with detachable braided crossbody strap.'),
        ('Wallet Case (R6)',     'wallet-r6',     99.0, 'Card-holding case with Find My pairing.'),
        ('Aluminum Bumper (R6)', 'bumper-r6',     69.0, '100% recycled aluminum bumper with MagSafe-compatible interior.'),
    ]
    for model_name, _model_slug, model_id in iphone_17_models:
        for color in iphone_17_colors:
            for style_name, style_id, price, desc in case_styles:
                color_slug = color.lower().replace(' ', '-')
                slug = f'r6-case-{style_id}-{model_id}-{color_slug}'
                name = f'{style_name} for {model_name} - {color}'
                specs = _r6_specs(
                    {'kind': 'iPhone Case', 'compatible_with': model_name,
                     'material': style_name.split('(')[0].strip(),
                     'magsafe_compatible': True, 'finish': color},
                    env=('Recycled polycarbonate and 95% recycled aluminum where applicable.' if 'Bumper' in style_name else '35% recycled silicone and 100% fiber-based packaging.'),
                    a11y=['Tactile color-coded edges aid identification for low-vision users'],
                    in_box=[f'{style_name} for {model_name}', 'Apple cleaning notice'],
                    whats_new='R6 — Adds Find My pairing for case + cross-product color matching with Watch bands.',
                    compatibility=[model_name],
                    breadcrumb=f'Shop > iPhone > Accessories > Cases > {model_name}',
                )
                extra.append((name, slug, 'accessories', 'iphone-case',
                              f'{name}. {desc}',
                              f'{name}. {desc} Designed exclusively for {model_name}. Fully MagSafe compatible.',
                              price, None, [color], [], specs, 2026, ''))

    # B. Apple Watch band colorways — 5 styles × 8 colors × 2 sizes = 80 SKUs
    band_styles = [
        ('Sport Loop (R6)',        'sport-loop-r6',    49.0,  'Soft, breathable, double-layer nylon weave.'),
        ('Braided Solo Loop (R6)', 'braided-solo-r6',  99.0,  'Recycled yarn woven into a stretchable single piece.'),
        ('Modern Buckle (R6)',     'modern-buckle-r6', 149.0, 'Granada leather with magnetic clasp.'),
        ('Milanese Loop (R6)',     'milanese-r6',      149.0, 'Stainless steel mesh with magnetic closure.'),
        ('Alpine Loop (R6)',       'alpine-loop-r6',   119.0, 'Reinforced loops + G-hook for Apple Watch Ultra.'),
    ]
    band_colors = ['Black','Storm Blue','Lake Green','Sand','Plum','Cypress','Ochre','Silver']
    band_sizes = [('41/42mm','41-42'),('45/49mm','45-49')]
    for style_name, style_id, price, desc in band_styles:
        for color in band_colors:
            for size_label, size_id in band_sizes:
                color_slug = color.lower().replace(' ', '-')
                slug = f'r6-band-{style_id}-{size_id}-{color_slug}'
                name = f'{style_name} - {color} - {size_label}'
                specs = _r6_specs(
                    {'kind': 'Apple Watch Band', 'style': style_name.split('(')[0].strip(),
                     'finish': color, 'case_size_compat': size_label,
                     'attachment': ('Magnetic' if ('Modern Buckle' in style_name or 'Milanese' in style_name) else 'Standard Apple Watch lug')},
                    env='Recycled yarn or fluoroelastomer; fiber-based packaging.',
                    a11y=['Tactile texture differs by style — aids identification by feel'],
                    in_box=[f'{style_name} band in {color}'],
                    whats_new=f'R6 — {color} colorway joins the {style_name.split("(")[0].strip()} line.',
                    compatibility=['Apple Watch Series 9-11','Apple Watch SE 2','Apple Watch Ultra 2-3'],
                    breadcrumb=f'Shop > Apple Watch > Bands > {style_name.split("(")[0].strip()}',
                )
                extra.append((name, slug, 'watch', 'watch-band',
                              f'{name}. {desc}',
                              f'{name}. {desc} For {size_label} Apple Watch cases.',
                              price, None, [color], [size_label], specs, 2026, ''))

    # C. HomeKit / Matter accessories — 50 SKUs.
    homekit_skus = [
        ('Aqara Door Sensor P2 - R6',                'r6-hk-aqara-door-p2',           17.99,'sensor'),
        ('Aqara Motion Sensor P2 - R6',              'r6-hk-aqara-motion-p2',         34.99,'sensor'),
        ('Aqara Water Leak Sensor - R6',             'r6-hk-aqara-leak',              22.99,'sensor'),
        ('Aqara Climate Sensor T1 - R6',             'r6-hk-aqara-climate-t1',        29.99,'sensor'),
        ('Aqara Camera Hub G3 - R6',                 'r6-hk-aqara-cam-g3',           139.99,'camera'),
        ('Aqara M3 Matter Hub - R6',                 'r6-hk-aqara-m3',                99.99,'hub'),
        ('Aqara Smart Lock U200 - R6',               'r6-hk-aqara-u200',             249.99,'lock'),
        ('Eve Energy Smart Plug 2nd Gen - R6',       'r6-hk-eve-energy-2g',           39.95,'plug'),
        ('Eve Energy Outdoor - R6',                  'r6-hk-eve-energy-outdoor',      49.95,'plug'),
        ('Eve Door & Window Contact - R6',           'r6-hk-eve-door',                39.95,'sensor'),
        ('Eve Light Switch - R6',                    'r6-hk-eve-switch',              49.95,'switch'),
        ('Eve Aqua Hose Controller - R6',            'r6-hk-eve-aqua',               149.95,'irrigation'),
        ('Eve MotionBlinds Bridge - R6',             'r6-hk-eve-mb-bridge',          129.95,'hub'),
        ('Eve Thermo Radiator Valve (3pk) - R6',     'r6-hk-eve-thermo-3pk',         179.85,'thermo'),
        ('Eve Weather Outdoor Station - R6',         'r6-hk-eve-weather',             69.95,'sensor'),
        ('Philips Hue White Starter Kit (4pk) - R6', 'r6-hk-hue-white-4pk',           99.99,'light'),
        ('Philips Hue Color Starter Kit (3pk) - R6', 'r6-hk-hue-color-3pk',          179.99,'light'),
        ('Philips Hue Lightstrip Plus 2m - R6',      'r6-hk-hue-strip-2m',            89.99,'light'),
        ('Philips Hue Play Light Bar (2pk) - R6',    'r6-hk-hue-play-2pk',           139.99,'light'),
        ('Philips Hue Bridge 2nd Gen - R6',          'r6-hk-hue-bridge-2g',           59.99,'hub'),
        ('Philips Hue Tap Dial Switch - R6',         'r6-hk-hue-tap-dial',            49.99,'switch'),
        ('Philips Hue Motion Outdoor - R6',          'r6-hk-hue-motion-out',          59.99,'sensor'),
        ('Logitech Circle View Doorbell - R6',       'r6-hk-circle-doorbell',        199.99,'doorbell'),
        ('Logitech Circle View Camera 2nd Gen - R6', 'r6-hk-circle-cam-2g',          179.99,'camera'),
        ('Logitech Pop Smart Button (3pk) - R6',     'r6-hk-pop-3pk',                 79.99,'switch'),
        ('Yale Assure Lock 2 Plus HomeKit - R6',     'r6-hk-yale-assure-plus',       299.99,'lock'),
        ('Yale Smart Cabinet Lock - R6',             'r6-hk-yale-cabinet',            89.99,'lock'),
        ('August WiFi Smart Lock 4th Gen - R6',      'r6-hk-august-4g',              229.99,'lock'),
        ('Schlage Encode Plus HomeKit - R6',         'r6-hk-schlage-encode-plus',    349.99,'lock'),
        ('Lutron Caseta Dimmer Kit HomeKit - R6',    'r6-hk-lutron-caseta',           99.95,'switch'),
        ('Lutron Caseta Fan Speed Control - R6',     'r6-hk-lutron-fan',              69.95,'switch'),
        ('Nanoleaf Shapes Mini Triangles (5pk) - R6','r6-hk-nano-mini-tri',           89.99,'light'),
        ('Nanoleaf Skylight Modular (3pk) - R6',     'r6-hk-nano-skylight-3pk',      299.99,'light'),
        ('Nanoleaf Lines 60 Square Lights - R6',     'r6-hk-nano-lines-60',          499.99,'light'),
        ('Nanoleaf 4D Screen Mirror Kit - R6',       'r6-hk-nano-4d',                119.99,'light'),
        ('LIFX Mini White HomeKit - R6',             'r6-hk-lifx-mini',               24.99,'light'),
        ('LIFX A19 Color HomeKit - R6',              'r6-hk-lifx-a19',                44.99,'light'),
        ('LIFX Beam HomeKit Lightstrip - R6',        'r6-hk-lifx-beam',              199.99,'light'),
        ('Meross Smart Plug Mini 4pk HomeKit - R6',  'r6-hk-meross-plug-4pk',         29.99,'plug'),
        ('Meross Garage Door Opener HomeKit - R6',   'r6-hk-meross-garage',           49.99,'garage'),
        ('Meross Smart Curtain Motor HomeKit - R6',  'r6-hk-meross-curtain',          89.99,'motor'),
        ('VOCOlinc Smart Bulb A19 (4pk) - R6',       'r6-hk-vocolinc-a19-4pk',        59.99,'light'),
        ('VOCOlinc Smart Strip HomeKit - R6',        'r6-hk-vocolinc-strip',          34.99,'light'),
        ('Onvis HomeKit Smart Plug EU - R6',         'r6-hk-onvis-plug-eu',           21.99,'plug'),
        ('Onvis Air Quality Sensor S5 - R6',         'r6-hk-onvis-air',               79.99,'sensor'),
        ('Tempo Bedroom Air Quality Monitor - R6',   'r6-hk-tempo-bedroom',           99.99,'sensor'),
        ('Netatmo Smart Doorbell HomeKit - R6',      'r6-hk-netatmo-doorbell',       299.99,'doorbell'),
        ('Netatmo Smart Weather Station - R6',       'r6-hk-netatmo-weather',        179.99,'sensor'),
        ('Ecobee Smart Thermostat Premium - R6',     'r6-hk-ecobee-premium',         249.99,'thermo'),
        ('Roborock S8 MaxV Ultra - R6',              'r6-hk-roborock-s8',           1799.99,'vacuum'),
    ]
    for name, slug, price, kind in homekit_skus:
        specs = _r6_specs(
            {'kind': 'HomeKit Accessory', 'category': kind,
             'compatible_with': 'iPhone, iPad, Mac, Apple Watch, HomePod',
             'protocols': (['HomeKit','Matter over Thread'] if kind in ('lock','sensor','plug','switch') else ['HomeKit'])},
            env='Fiber-based packaging. Apple-required end-of-life recycling supported.',
            a11y=['Voice control via Siri','Automations support haptic Lock Screen notifications'],
            in_box=[name,'HomeKit setup code card','Quick start guide'],
            whats_new='R6 — Adds Matter 1.3 support and Find My pairing where applicable.',
            compatibility=['iOS 18+','macOS 15+','HomePod (any)'],
            breadcrumb=f'Shop > Accessories > Smart Home > {kind.capitalize()}',
        )
        extra.append((name, slug, 'accessories', 'homekit',
                      f'{name}. HomeKit + Matter accessory.',
                      f'{name}. Adds Matter 1.3 support and Find My pairing where applicable.',
                      price, None, ['White'], [], specs, 2026, ''))

    # D. Apple Gift Card denominations — 14 amounts × 4 designs = 56.
    gift_amounts = [25,50,75,100,150,200,250,300,500,750,1000,1250,1500,2000]
    gift_designs = [('Classic','classic'),('Birthday','birthday'),
                    ('Holiday','holiday'),('Thank You','thanks')]
    for amt in gift_amounts:
        for design_name, design_id in gift_designs:
            slug = f'r6-giftcard-{design_id}-{amt}'
            name = f'Apple Gift Card - {design_name} - ${amt}'
            req_age = amt >= int(R6_AGEVERIFY_REQUIRED_MIN_USD)
            specs = _r6_specs(
                {'kind': 'Apple Gift Card', 'amount_usd': amt, 'design': design_name,
                 'delivery': 'Email within 24 hours',
                 'age_verification_required': req_age,
                 'redemption': 'apple.com, App Store, Apple Music, iCloud+, AppleCare'},
                env='Digital gift cards have zero physical packaging.',
                a11y=['Voice redemption via Siri','Large-print code option'],
                in_box=['Digital code via email'],
                whats_new='R6 — Adds Thank You + Holiday designs; age-verification flow at /gift-card.',
                compatibility=['Apple ID','Apple Wallet'],
                breadcrumb='Shop > Gift Cards',
            )
            extra.append((name, slug, 'accessories', 'gift-card',
                          f'{name}. ' + ('Age verification (18+) required at checkout.' if req_age else 'No age verification.'),
                          f'{name}. Digital Apple Gift Card. Use for any Apple product, service, or subscription. ' +
                          ('Cards $500+ require age verification at /gift-card.' if req_age else ''),
                          float(amt), None, [design_name], [], specs, 2026, ''))

    # E. Refurbished R6 — ~42 SKUs.
    refurb_seeds = [
        ('iPhone 15 (Refurbished) - 128GB - Black','iphone-15-refurb-128-black',629.0,'iphone','refurbished'),
        ('iPhone 15 (Refurbished) - 256GB - Blue','iphone-15-refurb-256-blue',729.0,'iphone','refurbished'),
        ('iPhone 15 Pro (Refurbished) - 128GB - Natural Titanium','iphone-15-pro-refurb-128-natural',849.0,'iphone','refurbished'),
        ('iPhone 15 Pro Max (Refurbished) - 256GB - Black Titanium','iphone-15-pro-max-refurb-256-black',1049.0,'iphone','refurbished'),
        ('iPhone 14 (Refurbished) - 128GB - Midnight','iphone-14-refurb-128-midnight',499.0,'iphone','refurbished'),
        ('iPhone 14 Pro (Refurbished) - 256GB - Deep Purple','iphone-14-pro-refurb-256-purple',799.0,'iphone','refurbished'),
        ('iPhone 13 (Refurbished) - 128GB - Starlight','iphone-13-refurb-128-starlight',399.0,'iphone','refurbished'),
        ('iPhone SE 3 (Refurbished) - 64GB - PRODUCT(RED)','iphone-se3-refurb-64-red',329.0,'iphone','refurbished'),
        ('MacBook Air M2 (Refurbished) - 8GB/256GB','macbook-air-m2-refurb-8-256',849.0,'mac','refurbished'),
        ('MacBook Air M2 (Refurbished) - 16GB/512GB','macbook-air-m2-refurb-16-512',1099.0,'mac','refurbished'),
        ('MacBook Air M3 (Refurbished) - 8GB/256GB','macbook-air-m3-refurb-8-256',929.0,'mac','refurbished'),
        ('MacBook Pro 14 M3 (Refurbished) - 16GB/512GB','macbook-pro-14-m3-refurb-16-512',1499.0,'mac','refurbished'),
        ('MacBook Pro 14 M3 Pro (Refurbished) - 18GB/512GB','macbook-pro-14-m3-pro-refurb-18-512',1799.0,'mac','refurbished'),
        ('MacBook Pro 16 M3 Max (Refurbished) - 36GB/1TB','macbook-pro-16-m3-max-refurb-36-1tb',2899.0,'mac','refurbished'),
        ('Mac mini M2 (Refurbished) - 8GB/256GB','mac-mini-m2-refurb-8-256',509.0,'mac','refurbished'),
        ('Mac mini M2 Pro (Refurbished) - 16GB/512GB','mac-mini-m2-pro-refurb-16-512',1099.0,'mac','refurbished'),
        ('iPad Pro M2 11-inch (Refurbished) - 256GB Wi-Fi','ipad-pro-m2-11-refurb-256-wifi',759.0,'ipad','refurbished'),
        ('iPad Pro M2 12.9-inch (Refurbished) - 256GB','ipad-pro-m2-129-refurb-256',959.0,'ipad','refurbished'),
        ('iPad Air M2 (Refurbished) - 128GB Wi-Fi','ipad-air-m2-refurb-128-wifi',509.0,'ipad','refurbished'),
        ('iPad 10th Gen (Refurbished) - 64GB Wi-Fi','ipad-10-refurb-64-wifi',299.0,'ipad','refurbished'),
        ('iPad mini 6 (Refurbished) - 64GB','ipad-mini-6-refurb-64',389.0,'ipad','refurbished'),
        ('Apple Watch Series 9 (Refurbished) - 41mm GPS','watch-s9-refurb-41mm-gps',299.0,'watch','refurbished'),
        ('Apple Watch Series 9 (Refurbished) - 45mm Cell','watch-s9-refurb-45mm-cell',429.0,'watch','refurbished'),
        ('Apple Watch Ultra 2 (Refurbished) - 49mm','watch-ultra-2-refurb-49mm',699.0,'watch','refurbished'),
        ('AirPods Pro 2 (Refurbished) - USB-C','airpods-pro-2-refurb-usbc',189.0,'airpods','refurbished'),
        ('AirPods Max (Refurbished) - Silver','airpods-max-refurb-silver',449.0,'airpods','refurbished'),
        ('AirPods 3rd Gen (Refurbished)','airpods-3-refurb',139.0,'airpods','refurbished'),
        ('HomePod 2nd Gen (Refurbished) - White','homepod-2-refurb-white',249.0,'homepod','refurbished'),
        ('HomePod mini (Refurbished) - Space Gray','homepod-mini-refurb-spacegray',89.0,'homepod','refurbished'),
        ('Apple TV 4K (Refurbished) - 128GB Wi-Fi+Eth','apple-tv-4k-refurb-128',149.0,'tv','refurbished'),
        ('Apple TV 4K (Refurbished) - 64GB Wi-Fi','apple-tv-4k-refurb-64',119.0,'tv','refurbished'),
        ('Apple Vision Pro (Refurbished) - 256GB','vision-pro-refurb-256',2999.0,'vision','refurbished'),
        ('Studio Display Standard Tilt (Refurbished)','studio-display-st-refurb',1349.0,'mac','refurbished'),
        ('Pro Display XDR Standard (Refurbished)','pro-display-xdr-refurb',4499.0,'mac','refurbished'),
        ('Mac Studio M2 Max (Refurbished) - 32GB/512GB','mac-studio-m2-max-refurb-32-512',1699.0,'mac','refurbished'),
        ('Mac Studio M2 Ultra (Refurbished) - 64GB/1TB','mac-studio-m2-ultra-refurb-64-1tb',3699.0,'mac','refurbished'),
        ('Mac Pro Tower M2 Ultra (Refurbished) - 64GB/1TB','mac-pro-m2-ultra-refurb-64-1tb',5599.0,'mac','refurbished'),
        ('iMac 24-inch M3 (Refurbished) - 8GB/256GB','imac-24-m3-refurb-8-256',1099.0,'mac','refurbished'),
        ('iMac 24-inch M3 (Refurbished) - 16GB/512GB','imac-24-m3-refurb-16-512',1349.0,'mac','refurbished'),
        ('iPhone 16 (Refurbished) - 128GB - Black','iphone-16-refurb-128-black',679.0,'iphone','refurbished'),
        ('iPhone 16 Plus (Refurbished) - 256GB - Pink','iphone-16-plus-refurb-256-pink',829.0,'iphone','refurbished'),
        ('iPhone 16 Pro (Refurbished) - 128GB - Desert Titanium','iphone-16-pro-refurb-128-desert',899.0,'iphone','refurbished'),
        ('iPhone 16 Pro Max (Refurbished) - 256GB - Black Titanium','iphone-16-pro-max-refurb-256-black',1099.0,'iphone','refurbished'),
    ]
    for name, slug_base, price, cat, sub in refurb_seeds:
        slug = f'r6-refurb-{slug_base}'
        specs = _r6_specs(
            {'kind': 'Apple Certified Refurbished', 'condition': 'Excellent',
             'warranty': '1-year Apple Limited Warranty', 'returns': '14-day return window',
             'savings_vs_new': f'~${int(price * 0.18)} savings vs new'},
            env='Refurbished devices reduce e-waste. Tested, repackaged, reseated.',
            a11y=['Same accessibility features as new device'],
            in_box=[name,'USB-C cable','Refurbished documentation pack'],
            whats_new='R6 — Refurbished inventory now includes Vision Pro and Mac Pro Tower.',
            compatibility=[],
            breadcrumb=f'Shop > Refurbished > {cat.capitalize()}',
        )
        extra.append((name, slug, cat, sub,
                      f'{name}. Apple Certified Refurbished — 1-year warranty.',
                      f'{name}. Apple Certified Refurbished. Includes 1-year Apple limited warranty and 14-day returns.',
                      price, None, ['Refurbished'], [], specs, 2025, ''))

    # F. AppleCare R6 bundles — 32 SKUs.
    applecare_r6 = [
        ('AppleCare+ for iPhone 17 (24-month) - R6',                    'r6-ac-iphone-17-24m',       149.0,'iphone'),
        ('AppleCare+ for iPhone 17 Pro (24-month) - R6',                'r6-ac-iphone-17-pro-24m',   199.0,'iphone'),
        ('AppleCare+ for iPhone 17 Pro Max (24-month) - R6',            'r6-ac-iphone-17-pro-max-24m',229.0,'iphone'),
        ('AppleCare+ for iPhone Air (24-month) - R6',                   'r6-ac-iphone-air-24m',      169.0,'iphone'),
        ('AppleCare+ with Theft & Loss for iPhone 17 (24-month) - R6',  'r6-ac-iphone-17-tnl-24m',   219.0,'iphone'),
        ('AppleCare+ with Theft & Loss for iPhone 17 Pro (24-month) R6','r6-ac-iphone-17-pro-tnl-24m',269.0,'iphone'),
        ('AppleCare+ for iPhone 17 (monthly) - R6',                     'r6-ac-iphone-17-mo',          8.99,'iphone'),
        ('AppleCare+ for iPhone 17 Pro (monthly) - R6',                 'r6-ac-iphone-17-pro-mo',     11.99,'iphone'),
        ('AppleCare+ for MacBook Air 13 M3 (3-year) - R6',              'r6-ac-mba-13-m3',           199.0,'mac'),
        ('AppleCare+ for MacBook Air 15 M3 (3-year) - R6',              'r6-ac-mba-15-m3',           229.0,'mac'),
        ('AppleCare+ for MacBook Pro 14 (3-year) - R6',                 'r6-ac-mbp-14',              279.0,'mac'),
        ('AppleCare+ for MacBook Pro 16 (3-year) - R6',                 'r6-ac-mbp-16',              399.0,'mac'),
        ('AppleCare+ for iMac (3-year) - R6',                           'r6-ac-imac',                169.0,'mac'),
        ('AppleCare+ for Mac mini (3-year) - R6',                       'r6-ac-mac-mini',             99.0,'mac'),
        ('AppleCare+ for Mac Studio (3-year) - R6',                     'r6-ac-mac-studio',          199.0,'mac'),
        ('AppleCare+ for Mac Pro (3-year) - R6',                        'r6-ac-mac-pro',             299.0,'mac'),
        ('AppleCare+ for iPad Pro M5 (2-year) - R6',                    'r6-ac-ipad-pro-m5',         149.0,'ipad'),
        ('AppleCare+ for iPad Air M4 (2-year) - R6',                    'r6-ac-ipad-air-m4',          99.0,'ipad'),
        ('AppleCare+ for iPad (2-year) - R6',                           'r6-ac-ipad',                 79.0,'ipad'),
        ('AppleCare+ for iPad mini (2-year) - R6',                      'r6-ac-ipad-mini',            79.0,'ipad'),
        ('AppleCare+ for Apple Watch Series 11 (2-year) - R6',          'r6-ac-watch-s11',            49.0,'watch'),
        ('AppleCare+ for Apple Watch Ultra 3 (2-year) - R6',            'r6-ac-watch-ultra-3',        99.0,'watch'),
        ('AppleCare+ for Apple Watch SE 2 (2-year) - R6',               'r6-ac-watch-se-2',           49.0,'watch'),
        ('AppleCare+ for AirPods Pro 3 (2-year) - R6',                  'r6-ac-airpods-pro-3',        29.0,'airpods'),
        ('AppleCare+ for AirPods 4 (2-year) - R6',                      'r6-ac-airpods-4',            29.0,'airpods'),
        ('AppleCare+ for AirPods Max 2 (2-year) - R6',                  'r6-ac-airpods-max-2',        59.0,'airpods'),
        ('AppleCare+ for HomePod (2-year) - R6',                        'r6-ac-homepod-2',            39.0,'homepod'),
        ('AppleCare+ for HomePod mini (2-year) - R6',                   'r6-ac-homepod-mini',         15.0,'homepod'),
        ('AppleCare+ for Apple Vision Pro (2-year) - R6',               'r6-ac-vision-pro',          499.0,'vision'),
        ('AppleCare+ for Apple TV 4K (2-year) - R6',                    'r6-ac-tv-4k',                29.0,'tv'),
        ('AppleCare Bundle — Family (iPhone+Watch+iPad+Mac) - R6',      'r6-ac-bundle-family',       799.0,'accessories'),
        ('AppleCare Bundle — Pro Studio (Mac+Display+Pencil) - R6',     'r6-ac-bundle-pro-studio',   599.0,'accessories'),
    ]
    for name, slug, price, target_cat in applecare_r6:
        specs = _r6_specs(
            {'kind': 'AppleCare+', 'target': target_cat,
             'coverage': '2-3 years of accidental damage protection + 24/7 Apple expert support',
             'theft_and_loss': ('tnl' in slug)},
            env='Service shipping uses carbon-neutral logistics.',
            a11y=['Service appointments accept VoiceOver bookings'],
            in_box=['Coverage certificate (digital)'],
            whats_new='R6 — Adds monthly billing option for iPhone AppleCare and Theft & Loss for Pro models.',
            compatibility=[target_cat],
            breadcrumb=f'Shop > AppleCare+ > {target_cat.capitalize()}',
        )
        extra.append((name, slug, 'accessories', 'applecare',
                      f'{name}. Apple-trained service + accidental damage coverage.',
                      f'{name}. Full coverage from Apple-trained specialists. 24/7 priority access to Apple support.',
                      price, None, ['Service'], [], specs, 2026, ''))

    # G. Sustainability — 20 SKUs.
    sustain_skus = [
        ('100% Recycled USB-C Cable 1m - R6','r6-sustain-usbc-1m',19.0,'cable'),
        ('100% Recycled USB-C Cable 2m - R6','r6-sustain-usbc-2m',29.0,'cable'),
        ('100% Recycled MagSafe Charger 1m - R6','r6-sustain-magsafe-1m',39.0,'charger'),
        ('100% Recycled MagSafe Charger 2m - R6','r6-sustain-magsafe-2m',49.0,'charger'),
        ('Recycled Aluminum Stand - iPhone - R6','r6-sustain-stand-iphone',49.0,'stand'),
        ('Recycled Aluminum Stand - iPad - R6','r6-sustain-stand-ipad',69.0,'stand'),
        ('Recycled Aluminum Stand - MacBook - R6','r6-sustain-stand-macbook',79.0,'stand'),
        ('Recycled Polishing Cloth (R6) - 3 pack','r6-sustain-cloth-3pk',39.0,'cleaning'),
        ('Recycled Apple Pencil Carry Pouch (R6)','r6-sustain-pencil-pouch',29.0,'case'),
        ('Recycled FineWoven Sleeve - 13-inch (R6)','r6-sustain-sleeve-13',99.0,'sleeve'),
        ('Recycled FineWoven Sleeve - 14-inch (R6)','r6-sustain-sleeve-14',109.0,'sleeve'),
        ('Recycled FineWoven Sleeve - 15-inch (R6)','r6-sustain-sleeve-15',119.0,'sleeve'),
        ('Recycled FineWoven Sleeve - 16-inch (R6)','r6-sustain-sleeve-16',129.0,'sleeve'),
        ('Carbon-neutral Apple Watch Sport Band - R6','r6-sustain-watch-sport',49.0,'band'),
        ('Carbon-neutral Apple Watch Solo Loop - R6','r6-sustain-watch-solo',99.0,'band'),
        ('Recycled MagSafe Wallet (R6)','r6-sustain-magsafe-wallet',59.0,'wallet'),
        ('Recycled FineWoven AirTag Loop - R6','r6-sustain-airtag-loop',39.0,'loop'),
        ('Recycled FineWoven AirTag Key Ring - R6','r6-sustain-airtag-keyring',35.0,'loop'),
        ('Recycled iPad Smart Folio - R6','r6-sustain-ipad-folio',79.0,'folio'),
        ('Recycled Mac Magic Keyboard Sleeve - R6','r6-sustain-keyboard-sleeve',59.0,'sleeve'),
    ]
    for name, slug, price, kind in sustain_skus:
        specs = _r6_specs(
            {'kind': 'Sustainable Accessory', 'material': '100% recycled or carbon-neutral',
             'product_category': kind},
            env='Apple 2030 net-zero carbon. Fiber-based packaging.',
            a11y=['Tactile labels indicating recycled origin'],
            in_box=[name,'Apple Environmental Responsibility Report card'],
            whats_new='R6 — Joins Apple 2030 carbon-neutral lineup.',
            compatibility=['MagSafe','iPad Smart Connector','Apple Watch lugs'],
            breadcrumb=f'Shop > Apple Values > Environment > {kind.capitalize()}',
        )
        extra.append((name, slug, 'accessories', 'sustainable',
                      f'{name}. Carbon-neutral.',
                      f'{name}. Built with 100% recycled materials where applicable. Part of the Apple 2030 carbon-neutral lineup.',
                      price, None, ['Recycled'], [], specs, 2026, ''))

    # H. Apple Pencil tips + iPad keyboards — ~25 SKUs.
    pencil_models = [
        ('Apple Pencil Pro Replacement Tip','pencil-pro-tip',19.0),
        ('Apple Pencil USB-C Replacement Tip','pencil-usbc-tip',15.0),
        ('Apple Pencil (Gen 2) Replacement Tip','pencil-2-tip',19.0),
    ]
    pack_sizes = [('Single','single',1.0),('4-pack','4pk',3.5),('10-pack','10pk',8.0)]
    for pname, pslug, base in pencil_models:
        for size_label, size_id, mult in pack_sizes:
            slug = f'r6-acc-{pslug}-{size_id}'
            name = f'{pname} - {size_label} (R6)'
            specs = _r6_specs(
                {'kind': 'Apple Pencil Accessory', 'pack_size': size_label,
                 'compatible_with': pname.split(' Replacement')[0]},
                env='Tip housing uses 30% recycled plastic.',
                a11y=['Tactile pack-size markings'],
                in_box=[f'{size_label} of replacement tips'],
                whats_new='R6 — 10-pack bundles offered for fleet use.',
                compatibility=[pname.split(' Replacement')[0]],
                breadcrumb='Shop > Accessories > Apple Pencil > Tips',
            )
            extra.append((name, slug, 'accessories', 'pencil-tip',
                          f'{name}.', f'{name}. Replacement tips.',
                          round(base * mult, 2), None, ['White'], [size_label], specs, 2026, ''))

    mk_languages = ['US English','UK English','French','German','Spanish','Japanese','Korean','Italian',
                    'Portuguese (BR)','Chinese (Pinyin)','Arabic','Hebrew']
    mk_models = [
        ('Magic Keyboard for iPad Pro 11 (M4)','mk-ipp-11-m4',299.0),
        ('Magic Keyboard for iPad Pro 13 (M4)','mk-ipp-13-m4',349.0),
        ('Magic Keyboard for iPad Air 11 (M4)','mk-ia-11-m4',269.0),
        ('Magic Keyboard for iPad Air 13 (M4)','mk-ia-13-m4',319.0),
    ]
    for mname, mslug, price in mk_models:
        for lang in mk_languages:
            lang_slug = lang.lower().replace(' ', '-').replace('(', '').replace(')', '')
            slug = f'r6-{mslug}-{lang_slug}'
            name = f'{mname} - {lang}'
            specs = _r6_specs(
                {'kind':'iPad Keyboard','language':lang,'model':mname,
                 'glass_trackpad':True,'function_row':True},
                env='Recycled aluminum palm rest. Fiber-based packaging.',
                a11y=['Backlit keys','Adjustable trackpad sensitivity','Accessibility shortcuts row'],
                in_box=[mname,'USB-C-to-USB-C cable'],
                whats_new='R6 — Adds 12 keyboard layouts including Arabic and Hebrew.',
                compatibility=[mname.split(' for ')[1]],
                breadcrumb='Shop > iPad > Accessories > Keyboards',
            )
            extra.append((name, slug, 'accessories', 'ipad-keyboard',
                          f'{name}.', f'{name}. With glass trackpad and function row.',
                          price, None, ['Black','White'], [], specs, 2026, ''))

    # I. Apple Watch case finish matrix — 3 case lines × 4 finishes × 2 sizes = 24 SKUs.
    watch_cases = [
        ('Apple Watch Series 11', 'watch-s11', 399.0),
        ('Apple Watch SE 2',      'watch-se-2', 249.0),
        ('Apple Watch Ultra 3',   'watch-ultra-3', 799.0),
    ]
    watch_finishes = [
        ('Aluminum',        'aluminum'),
        ('Stainless Steel', 'steel'),
        ('Titanium',        'titanium'),
        ('Polished Black',  'black-polish'),
    ]
    watch_case_sizes = [('41mm', '41'), ('45mm', '45')]
    for wname, wslug, base_price in watch_cases:
        for finish, finish_id in watch_finishes:
            for size_label, size_id in watch_case_sizes:
                # Ultra is 49mm only — skip 41/45 for Ultra.
                if 'Ultra' in wname and size_id == '41':
                    continue
                slug = f'r6-watchcase-{wslug}-{finish_id}-{size_id}'
                # Pricing delta by finish.
                delta = {'aluminum':0, 'steel':200, 'titanium':300, 'black-polish':250}.get(finish_id, 0)
                if 'Ultra' in wname:
                    size_label = '49mm'
                price = base_price + delta
                name = f'{wname} - {finish} Case - {size_label}'
                specs = _r6_specs(
                    {'kind':'Apple Watch Case', 'series':wname, 'finish':finish, 'case_size':size_label,
                     'sapphire_crystal': finish != 'Aluminum'},
                    env='Aluminum case is 100% recycled. Stainless Steel and Titanium use ≥50% recycled content.',
                    a11y=['VoiceOver fully supported','Always-On retina display','AssistiveTouch'],
                    in_box=[wname, 'Sport Loop band','USB-C Magnetic Charging Cable'],
                    whats_new=f'R6 — {finish} finish joins the {wname} line.',
                    compatibility=['iPhone XS or later (iOS 18+)'],
                    breadcrumb=f'Shop > Apple Watch > {wname} > {finish}',
                )
                extra.append((name, slug, 'watch', 'watch-case',
                              f'{name}.', f'{name}. {finish} finish with sapphire crystal where applicable.',
                              price, round(price/24, 2), [finish], [size_label], specs, 2026, ''))

    # J. MagSafe + Find My peripherals — 30 SKUs.
    magsafe_skus = [
        ('MagSafe Battery Pack 10000mAh - R6',          'r6-mag-battery-10k',          99.0),
        ('MagSafe Battery Pack 5000mAh - R6',           'r6-mag-battery-5k',           69.0),
        ('MagSafe Duo Charger 2nd Gen - R6',            'r6-mag-duo-2g',              129.0),
        ('MagSafe 3-in-1 Charging Stand - R6',          'r6-mag-3in1-stand',          149.0),
        ('MagSafe Travel Charger Foldable - R6',        'r6-mag-travel-fold',          79.0),
        ('MagSafe Car Vent Mount Qi2 - R6',             'r6-mag-car-vent',             49.0),
        ('MagSafe Car Dash Mount Qi2 - R6',             'r6-mag-car-dash',             59.0),
        ('MagSafe Car Wireless Charger - R6',           'r6-mag-car-wireless',         89.0),
        ('MagSafe Bedside Stand Black - R6',            'r6-mag-bedside-black',        69.0),
        ('MagSafe Bedside Stand Walnut - R6',           'r6-mag-bedside-walnut',       79.0),
        ('AirTag 4-pack with FineWoven Loops - R6',     'r6-mag-airtag-4pk-loops',    129.0),
        ('AirTag 8-pack with Key Rings - R6',           'r6-mag-airtag-8pk-keyrings', 199.0),
        ('AirTag Luggage Tag Genuine Leather - R6',     'r6-mag-airtag-luggage',       39.0),
        ('AirTag Pet Collar Mount - R6',                'r6-mag-airtag-pet',           29.0),
        ('AirTag Bike Mount with Lock - R6',            'r6-mag-airtag-bike',          39.0),
        ('Find My Beacon Wallet (Leather) - R6',        'r6-fm-wallet-leather',        99.0),
        ('Find My Beacon Backpack Insert - R6',         'r6-fm-bp-insert',             49.0),
        ('Find My Beacon Headphone Strap - R6',         'r6-fm-headphone-strap',       29.0),
        ('Find My Beacon Smart Tag (5pk) - R6',         'r6-fm-tag-5pk',              149.0),
        ('Find My Tile-compatible Beacon - R6',         'r6-fm-tile-compat',           34.0),
        ('Qi2 Wireless Charger 15W Round - R6',         'r6-qi2-15w-round',            49.0),
        ('Qi2 Wireless Charger 15W Square - R6',        'r6-qi2-15w-square',           49.0),
        ('Qi2 Tabletop Wireless Charger - R6',          'r6-qi2-tabletop',             79.0),
        ('Qi2 Stand for AirPods + iPhone - R6',         'r6-qi2-airpods-stand',        69.0),
        ('Qi2 Pocket Wireless Charger USB-C - R6',      'r6-qi2-pocket-usbc',          39.0),
        ('USB-C 5K Display Cable 1m - R6',              'r6-usbc-5k-1m',               29.0),
        ('USB-C 5K Display Cable 2m - R6',              'r6-usbc-5k-2m',               39.0),
        ('USB-C Thunderbolt 4 Pro Cable 3m - R6',       'r6-usbc-tb4-3m',             159.0),
        ('USB-C Thunderbolt 4 Pro Cable 5m - R6',       'r6-usbc-tb4-5m',             199.0),
        ('USB-C to Lightning Adapter Bundle - R6',      'r6-usbc-lightning-bundle',    39.0),
    ]
    for name, slug, price in magsafe_skus:
        kind = 'MagSafe' if 'MagSafe' in name else ('Find My' if 'Find My' in name else ('Qi2' if 'Qi2' in name else 'USB-C'))
        specs = _r6_specs(
            {'kind': kind, 'wattage': ('15W' if 'Qi2 15W' in name or 'MagSafe' in name else 'N/A'),
             'find_my_compatible': ('Find My' in kind or 'AirTag' in name)},
            env='Body uses 30%+ recycled plastics. Fiber-based retail packaging.',
            a11y=['Tactile alignment dot to aid sightless placement'],
            in_box=[name,'USB-C to USB-C cable','Apple safety + recycling notice'],
            whats_new='R6 — Adds Qi2 15W universal stand line and Find My beacon SKUs.',
            compatibility=['iPhone 12+','AirPods (any)','Apple Watch with Qi2 module'],
            breadcrumb=f'Shop > Accessories > Power & Cables > {kind}',
        )
        extra.append((name, slug, 'accessories', 'magsafe',
                      f'{name}.', f'{name}. {kind} accessory.',
                      price, None, ['Black','White'], [], specs, 2026, ''))

    return extra


EXTRA_PRODUCTS_R6 = _extend_r6()


def _seed_extra_products():
    """Add the EXTRA_PRODUCTS + EXTRA_PRODUCTS_R2 + EXTRA_PRODUCTS_R3 + EXTRA_PRODUCTS_R4 + EXTRA_PRODUCTS_R5 + EXTRA_PRODUCTS_R6 rows. Idempotent — skips slugs already present."""
    existing = {p.slug for p in Product.query.with_entities(Product.slug).all()}
    added = 0
    for tup in (EXTRA_PRODUCTS + EXTRA_PRODUCTS_R2 + EXTRA_PRODUCTS_R3 + EXTRA_PRODUCTS_R4 + EXTRA_PRODUCTS_R5 + EXTRA_PRODUCTS_R6):
        (name, slug, cat, subcat, subt, desc, price, mp, colors, storage, specs, year, chip) = tup
        if slug in existing:
            continue
        img_base = slug.replace('-', '_')
        p = Product(
            name=name, slug=slug, category=cat, subcategory=subcat,
            subtitle=subt, description=desc,
            price=price, monthly_price=mp, months=(24 if mp else 0),
            is_new=False, is_featured=False,
            image=f'/static/images/products/{img_base}.jpg',
            hero_image=f'/static/images/hero/{img_base}_hero.jpg',
            color_options=json.dumps(colors),
            storage_options=json.dumps(storage),
            specs=json.dumps(specs),
            release_year=year, chip_family=chip,
            created_at=MIRROR_REFERENCE_DATE,
        )
        db.session.add(p)
        existing.add(slug)
        added += 1
    db.session.commit()
    print(f"Seeded {added} extra products")


# ---------------------------------------------------------------------------
# Reviews + Wishlist
# ---------------------------------------------------------------------------

REVIEW_TEMPLATES = [
    (5, 'Absolutely love it',
     'Honestly the best Apple purchase I have made in years. Battery life is fantastic and the build quality feels premium. Highly recommend.'),
    (5, 'Worth every penny',
     'Setup was effortless and it pairs beautifully with the rest of my Apple devices. Audio and display quality are top-tier.'),
    (5, 'Best in class',
     'I have tried competitors and nothing comes close. The ecosystem integration alone justifies the price.'),
    (4, 'Great upgrade',
     'Coming from a two-year-old model, the performance jump is noticeable. Camera in low light is much improved. Minor learning curve.'),
    (4, 'Solid choice',
     'Does everything I need and then some. The fit and finish are excellent. Lost half a star because the price still stings.'),
    (4, 'Recommended',
     'Bought one for my partner and ended up using it more than they did. Comfortable, light, and feels durable.'),
    (5, 'Game changer for my workflow',
     'Editing photos and exporting video on this is dramatically faster than my old setup. Saved me hours each week.'),
    (3, 'Good but not great',
     'It works as advertised. I expected a bigger leap considering the price tag, but it is still reliable and well built.'),
    (5, 'Bought one for the family',
     'Ended up buying a second one. Both my kids and I use it daily without complaints. Sound quality surprised me.'),
    (4, 'Beautiful design',
     'Looks even better in person. The color is gorgeous and the weight balance feels right. Battery could be better.'),
    (5, 'Apple at its best',
     'Every detail is considered. The packaging, the haptics, the software polish — this is why I keep coming back.'),
    (4, 'Worth the upgrade',
     'My previous device was three generations old. This feels significantly faster, especially for gaming and AR apps.'),
    (2, 'Not for me',
     'Returned mine within the window. The new design just did not click for me, although the screen is undeniably beautiful.'),
    (5, 'Battery is the real winner',
     'I genuinely make it through two full days of mixed use on a single charge. Cameras are great but the battery sealed the deal.'),
    (4, 'Loud and clear',
     'Speakers fill the room without distortion. I use it daily for calls and music and have zero complaints.'),
    (5, 'Snappy and stable',
     'Zero lag, zero crashes, even with heavy multitasking. Worth the wait through the launch backorder.'),
    (3, 'Mixed feelings',
     'The hardware is great but I am still adjusting to the software changes. Will revise once I have used it longer.'),
    (5, 'Recommend without hesitation',
     'If you are on the fence, jump. Setup was 10 minutes, transfer was painless, and it just works.'),
    (4, 'Surprisingly compact',
     'Lighter than I expected for what it does. Easy to carry on commutes and travel without feeling fragile.'),
    (5, 'Five years of Apple, never disappointed',
     'I have replaced every device in my household with Apple over the past five years and this continues the streak.'),
]

# Slugs to seed reviews against (top-N by sales-proxy: featured + flagship lines)
REVIEW_TARGET_SLUGS = [
    'iphone-17-pro', 'iphone-17-pro-max', 'iphone-air', 'iphone-17', 'iphone-17e',
    'iphone-15', 'iphone-15-pro', 'iphone-15-pro-max', 'iphone-14', 'iphone-13',
    'macbook-pro-14', 'macbook-pro-16', 'macbook-air-13', 'macbook-air-15',
    'macbook-air-13-inch-m3', 'imac-24', 'mac-mini-m4',
    'ipad-pro-m5', 'ipad-air-m4', 'ipad-10', 'ipad-mini-7',
    'apple-watch-series-11', 'apple-watch-ultra-3', 'apple-watch-series-10',
    'airpods-pro-3', 'airpods-max-2', 'airpods-4',
    'apple-vision-pro', 'homepod-2nd-gen', 'apple-tv-4k',
]

# R3 expansion: 100+ additional review targets across the entire catalog.
REVIEW_TARGET_SLUGS_R3 = [
    # iPhone — additional legacy SKUs
    'iphone-16', 'iphone-16-plus', 'iphone-16-pro', 'iphone-16-pro-max',
    'iphone-15-plus', 'iphone-14-pro', 'iphone-14-pro-max', 'iphone-14-plus',
    'iphone-13-pro', 'iphone-13-pro-max', 'iphone-13-mini',
    'iphone-12', 'iphone-12-pro', 'iphone-12-pro-max', 'iphone-12-mini',
    'iphone-11', 'iphone-11-pro', 'iphone-se-3', 'iphone-se-2nd-gen',
    # Mac — additional configurations and legacy SKUs
    'macbook-neo', 'macbook-air-15-inch-m3', 'macbook-pro-14-inch-m4',
    'macbook-pro-14-inch-m4-pro', 'macbook-pro-16-inch-m4-pro', 'macbook-pro-16-inch-m4-max',
    'macbook-air-13-inch-m2', 'macbook-air-15-inch-m2', 'imac-24-inch-m4',
    'mac-mini-m4-pro', 'mac-studio-m2-max', 'mac-studio-m2-ultra',
    # iPad
    'ipad-pro-13-inch-m4', 'ipad-pro-11-inch-m4', 'ipad-air-13-inch-m4',
    'ipad-air-11-inch-m4', 'ipad-a16', 'ipad-mini', 'ipad-mini-6',
    # Watch
    'apple-watch-ultra-2', 'apple-watch-series-9', 'apple-watch-series-8',
    'apple-watch-se', 'apple-watch-se-2', 'apple-watch-hermes-series-10',
    # AirPods / audio
    'airpods-pro-2-usb-c', 'airpods-3-magsafe', 'beats-studio-pro',
    'beats-studio-buds-plus', 'beats-fit-pro', 'beats-solo-4', 'beats-pill',
    'beats-pill-statement-red', 'beats-studio-pro-sandstone', 'beats-solo-4-matte-black',
    'beats-powerbeats-pro',
    # Vision / TV / HomePod
    'homepod-mini', 'homepod-2', 'apple-tv-hd', 'siri-remote-3rd-gen',
    # Accessories — high-traffic
    'apple-pencil-pro', 'apple-pencil-usb-c', 'magic-keyboard-ipad',
    'airtag', 'airtag-4-pack', 'magsafe-charger-1m', 'magsafe-charger-2m',
    'magsafe-duo-charger', 'magic-mouse-white', 'magic-trackpad-white',
    'magic-keyboard-touch-id', 'magic-keyboard-touch-id-numeric',
    'studio-display-standard-tilt', 'studio-display-nano-tilt', 'pro-display-xdr-standard',
    'usb-c-power-adapter-20w', 'usb-c-power-adapter-67w', 'usb-c-power-adapter-140w',
    'world-travel-adapter-kit', 'usb-c-digital-av-multiport',
    'smart-folio-ipad-pro-13-m4-black', 'magic-keyboard-ipad-pro-13-m4-black',
    'iphone-17-pro-max-silicone-black', 'iphone-air-silicone-midnight',
    'iphone-finewoven-wallet-black',
    # Watch bands — popular ones
    'sport-band-41mm-black', 'trail-loop-49mm-black-gray', 'alpine-loop-49mm-black',
    'ocean-band-49mm-tide-blue', 'link-bracelet-45mm-silver', 'milanese-41mm-silver',
    'braided-solo-41mm-black', 'nike-sport-41mm-black-black',
    # HomeKit
    'eve-energy-smart-plug', 'philips-hue-color-starter', 'nanoleaf-shapes-hexagons',
    'logitech-circle-view-camera', 'yale-assure-lock-2-homekit', 'aqara-m2-hub',
    # Services
    'apple-music-individual', 'apple-music-family', 'apple-tv-plus',
    'icloud-200gb', 'icloud-2tb', 'apple-arcade', 'apple-fitness-plus',
    'apple-one-family', 'apple-one-premier', 'apple-news-plus',
    # AppleCare
    'applecare-iphone-17-pro', 'applecare-macbook-pro-14', 'applecare-vision-pro',
    'applecare-ipad-pro-13', 'applecare-watch-ultra-3',
]

REVIEW_TEMPLATES_R3 = [
    (5, 'Exactly what I expected from Apple',
     'Setup was seamless. iCloud synced everything within minutes and Continuity with my other Apple devices just works. No regrets at this price point.'),
    (4, 'Great after the first week',
     'Took a few days to dial in my settings, but performance is excellent and battery life beats my last device by a noticeable margin.'),
    (5, 'Build quality is unmatched',
     'The materials, the weight balance, the finish — Apple still leads on physical product quality. Worth the wait.'),
    (3, 'Good, not life-changing',
     'Solid product, but the gap from my previous generation is smaller than the marketing suggests. Still glad I upgraded.'),
    (5, 'My go-to recommendation',
     'I have already recommended this to three friends. The combination of performance and ecosystem integration is hard to beat.'),
    (4, 'Subtle but meaningful improvements',
     'The headline specs do not tell the whole story — the everyday quality-of-life improvements add up over the first month.'),
    (5, 'Setup in 10 minutes',
     'Quick Start transferred everything from my old device. Apps, settings, passwords — all there when I picked it up.'),
    (4, 'Premium price, premium product',
     'Yes, it is expensive. But after a month of daily use I have no buyer\'s remorse. Build quality and software fluency carry the price.'),
    (3, 'Wish the upgrade path was clearer',
     'The product itself is great. The model lineup is confusing — took me a while to figure out which configuration I actually wanted.'),
    (5, 'Family is happy too',
     'Bought one for myself and ended up getting a second for my partner. Apple ecosystem benefits really kick in across multiple devices.'),
    (4, 'Solid daily driver',
     'I have used this every day for a month — zero issues, zero complaints. Does exactly what it advertises.'),
    (5, 'Worth the trade-in',
     'Traded in my older device and the credit covered nearly a third of this one. Trade-in process was smooth.'),
    (2, 'Returned within the window',
     'The hardware is great but it just was not the right fit for my workflow. Returns were painless — refund hit my card in 3 days.'),
    (5, 'AppleCare paid off already',
     'Glad I added AppleCare+ — already needed a battery service which would have been pricey without coverage.'),
    (4, 'Software is the unsung hero',
     'The hardware grabs the headlines, but the real reason I keep buying Apple is how much the software does for me without thinking about it.'),
]


def seed_reviews_and_wishlist():
    """Populate Review and WishlistItem with deterministic synthetic data.
    Skipped if either table already has rows.
    """
    if Review.query.first() and WishlistItem.query.first():
        return

    users = User.query.order_by(User.id).all()
    if not users:
        return

    # ---- Reviews ----
    if not Review.query.first():
        ix = 0
        # Base 30 slugs × 4 users = 120 reviews (R2 set).
        for slug in REVIEW_TARGET_SLUGS:
            p = Product.query.filter_by(slug=slug).first()
            if p is None:
                continue
            for j in range(len(users)):
                u = users[(ix + j) % len(users)]
                tpl = REVIEW_TEMPLATES[(ix + j) % len(REVIEW_TEMPLATES)]
                rating, title, body = tpl
                rev = Review(
                    user_id=u.id, product_id=p.id,
                    rating=rating, title=title, body=body,
                    created_at=MIRROR_REFERENCE_DATE - timedelta(days=(ix * 3 + j) % 240),
                )
                db.session.add(rev)
                ix += 1
        # R3 expansion: 4 reviews/slug × ~125 slugs = ~500 more reviews.
        # Cycles through the R3 template pool so reviews look distinct.
        for k, slug in enumerate(REVIEW_TARGET_SLUGS_R3):
            p = Product.query.filter_by(slug=slug).first()
            if p is None:
                continue
            for j in range(len(users)):
                u = users[(k + j) % len(users)]
                tpl = REVIEW_TEMPLATES_R3[(k * 2 + j) % len(REVIEW_TEMPLATES_R3)]
                rating, title, body = tpl
                rev = Review(
                    user_id=u.id, product_id=p.id,
                    rating=rating, title=title, body=body,
                    created_at=MIRROR_REFERENCE_DATE - timedelta(days=(k * 5 + j * 2) % 365 + 30),
                )
                db.session.add(rev)
        # Second pass on the most-trafficked products to push past 600.
        SECOND_PASS_SLUGS = [
            'iphone-17-pro', 'iphone-17-pro-max', 'iphone-air',
            'macbook-pro-14', 'macbook-pro-16', 'macbook-air-13',
            'ipad-pro-m5', 'apple-watch-ultra-3', 'apple-watch-series-11',
            'airpods-pro-3', 'apple-vision-pro',
        ]
        for k, slug in enumerate(SECOND_PASS_SLUGS):
            p = Product.query.filter_by(slug=slug).first()
            if p is None:
                continue
            for j in range(len(users)):
                u = users[(k + j + 1) % len(users)]
                tpl = REVIEW_TEMPLATES_R3[(k * 3 + j + 7) % len(REVIEW_TEMPLATES_R3)]
                rating, title, body = tpl
                rev = Review(
                    user_id=u.id, product_id=p.id,
                    rating=rating, title=title, body=body,
                    created_at=MIRROR_REFERENCE_DATE - timedelta(days=(k * 7 + j * 3) % 220 + 5),
                )
                db.session.add(rev)
        db.session.commit()
        print(f"Seeded {Review.query.count()} reviews")

    # ---- Wishlist ----
    if not WishlistItem.query.first():
        # R3: 16+ wishlist items per benchmark user, drawn from a wide span of
        # categories. Total 64+ rows across 4 users.
        wishlist_plan = [
            ('alice.j@test.com', [
                'iphone-17-pro-max', 'apple-watch-ultra-3', 'airpods-max-2', 'ipad-pro-m5',
                'magic-keyboard-ipad-pro-13-m4-black', 'apple-pencil-pro',
                'studio-display-standard-tilt', 'apple-vision-pro',
                'apple-tv-4k', 'homepod-2', 'iphone-17-pro-max-silicone-cypress',
                'airtag-4-pack', 'apple-one-premier', 'icloud-2tb',
                'applecare-iphone-17-pro-max', 'beats-studio-pro-sandstone',
            ]),
            ('bob.c@test.com',   [
                'macbook-pro-16', 'apple-vision-pro', 'studio-display', 'airpods-pro-3',
                'magic-mouse-black', 'magic-trackpad-black', 'magic-keyboard-touch-id-numeric',
                'pro-display-xdr-standard', 'usb-c-power-adapter-140w',
                'thunderbolt-4-pro-18m', 'mac-pro-tower', 'mac-studio-m2-ultra',
                'applecare-mac-studio', 'apple-music-family', 'beats-pill-matte-black',
                'logitech-mx-master-3s-mac',
            ]),
            ('carol.d@test.com', [
                'iphone-air', 'apple-watch-series-11', 'macbook-air-15', 'homepod-2',
                'airpods-4', 'ipad-air-m4', 'apple-pencil-pro',
                'smart-folio-ipad-air-11-m4-sage', 'iphone-air-silicone-green',
                'iphone-air-clear-magsafe', 'iphone-crossbody-strap-lake-green',
                'apple-music-individual', 'apple-fitness-plus', 'icloud-200gb',
                'eve-energy-smart-plug', 'philips-hue-color-starter',
            ]),
            ('david.k@test.com', [
                'iphone-17-pro', 'ipad-air-m4', 'apple-tv-4k', 'mac-studio-m2-ultra',
                'airpods-pro-3', 'apple-watch-ultra-3', 'trail-loop-49mm-black-gray',
                'alpine-loop-49mm-indigo', 'ocean-band-49mm-tide-blue',
                'magsafe-charger-2m', 'magsafe-duo-charger', 'world-travel-adapter-kit',
                'usb-c-digital-av-multiport', 'apple-one-family',
                'applecare-watch-ultra-3', 'applecare-iphone-17-pro',
            ]),
        ]
        offset = 0
        for email, slugs in wishlist_plan:
            u = User.query.filter_by(email=email).first()
            if not u:
                continue
            for slug in slugs:
                p = Product.query.filter_by(slug=slug).first()
                if not p:
                    continue
                db.session.add(WishlistItem(
                    user_id=u.id, product_id=p.id,
                    added_at=MIRROR_REFERENCE_DATE - timedelta(days=offset * 5),
                ))
                offset += 1
        db.session.commit()
        print(f"Seeded {WishlistItem.query.count()} wishlist items")


# ---------------------------------------------------------------------------
# Deterministic-seed wrapper + final layout normalization
# ---------------------------------------------------------------------------

def _pin_created_at_defaults():
    """Override `created_at` / `added_at` column defaults to MIRROR_REFERENCE_DATE
    for the duration of the seed pass. Without this, every fresh build stamps
    rows with the current wall clock and the resulting .db md5 drifts.
    Returns a list of (column, original_default) so the caller can restore.
    """
    from sqlalchemy.sql.schema import ColumnDefault
    pinned = []
    for tbl in db.metadata.tables.values():
        for col_name in ('created_at', 'added_at'):
            col = tbl.c.get(col_name)
            if col is None or col.default is None:
                continue
            pinned.append((col, col.default))
            col.default = ColumnDefault(MIRROR_REFERENCE_DATE)
    return pinned


def _restore_defaults(pinned):
    for col, original in pinned:
        col.default = original


def normalize_seed_db_layout():
    """Re-emit indexes in alpha order + VACUUM so rebuilds match byte-for-byte
    (SQLAlchemy iterates Table.indexes from a Python set, whose order depends
    on object id()s and therefore drifts across processes)."""
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


with app.app_context():
    db.create_all()
    pinned = _pin_created_at_defaults()
    try:
        seed_database()
        _seed_extra_products()
        seed_benchmark_users()
        seed_reviews_and_wishlist()
    finally:
        _restore_defaults(pinned)
    # Only normalize on the first build (when we just populated tables);
    # safe to always run since DROP/CREATE INDEX on the same name is idempotent.
    normalize_seed_db_layout()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
