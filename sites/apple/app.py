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
        TradeInValue(device='MacBook Pro', condition='good', value=500.00,
                     notes='Trade in your MacBook Pro for credit toward a new Mac.'),
        TradeInValue(device='MacBook Air', condition='good', value=350.00,
                     notes='Trade in your MacBook Air for credit toward a new Mac.'),
        TradeInValue(device='iPad Pro', condition='good', value=380.00,
                     notes='Trade in your iPad Pro for credit toward a new iPad.'),
        TradeInValue(device='Apple Watch', condition='good', value=120.00,
                     notes='Trade in your Apple Watch for credit toward a new Watch.'),
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


def _seed_extra_products():
    """Add the EXTRA_PRODUCTS rows. Idempotent — skips slugs already present."""
    existing = {p.slug for p in Product.query.with_entities(Product.slug).all()}
    added = 0
    for tup in EXTRA_PRODUCTS:
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
        for slug in REVIEW_TARGET_SLUGS:
            p = Product.query.filter_by(slug=slug).first()
            if p is None:
                continue
            # 4 reviews per product (one per user), cycled through templates.
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
        db.session.commit()
        print(f"Seeded {Review.query.count()} reviews")

    # ---- Wishlist ----
    if not WishlistItem.query.first():
        # 4 wishlist items per benchmark user, drawn from different categories.
        wishlist_plan = [
            ('alice.j@test.com', ['iphone-17-pro-max', 'apple-watch-ultra-3',
                                  'airpods-max-2', 'ipad-pro-m5']),
            ('bob.c@test.com',   ['macbook-pro-16', 'apple-vision-pro',
                                  'studio-display', 'airpods-pro-3']),
            ('carol.d@test.com', ['iphone-air', 'apple-watch-series-11',
                                  'macbook-air-15', 'homepod-2nd-gen']),
            ('david.k@test.com', ['iphone-17-pro', 'ipad-air-m4',
                                  'apple-tv-4k', 'mac-studio-m2-ultra']),
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
