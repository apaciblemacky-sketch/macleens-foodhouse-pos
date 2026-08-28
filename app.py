import os
import random
import string
from datetime import datetime, date, timedelta, time
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'macleens-hk-pos-2026-master')[cite: 12]

database_url = os.environ.get('DATABASE_URL')[cite: 12]
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)[cite: 12]

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///foodhouse_pos.db'[cite: 12]
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False[cite: 12]
app.config['SESSION_PERMANENT'] = True[cite: 12]
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=3650)[cite: 12]

db = SQLAlchemy(app)[cite: 12]

_DB_INITIALIZED = False

# ==================== DATA MODELS ====================

class StoreSetting(db.Model):
    __tablename__ = 'store_setting'
    id = db.Column(db.Integer, primary_key=True)[cite: 12]
    key = db.Column(db.String(50), unique=True, nullable=False)[cite: 12]
    value = db.Column(db.Text, nullable=False)[cite: 12]

class Staff(db.Model):
    __tablename__ = 'staff'
    id = db.Column(db.Integer, primary_key=True)[cite: 12]
    username = db.Column(db.String(50), unique=True, nullable=False)[cite: 12]
    pin_hash = db.Column(db.String(255), nullable=False)[cite: 12]
    role = db.Column(db.String(20), nullable=False)[cite: 12]
    active = db.Column(db.Boolean, default=True)[cite: 12]

class Customer(db.Model):
    __tablename__ = 'customer'
    id = db.Column(db.Integer, primary_key=True)[cite: 12]
    name = db.Column(db.String(100), nullable=False)[cite: 12]
    email = db.Column(db.String(120), nullable=True)[cite: 12]
    contact = db.Column(db.String(30), unique=True, nullable=False)[cite: 12]
    fb_messenger = db.Column(db.String(150), nullable=True)[cite: 12]
    pin_hash = db.Column(db.String(255), nullable=False)[cite: 12]
    profile_image = db.Column(db.Text, nullable=True)[cite: 12]
    default_address = db.Column(db.Text, nullable=True)[cite: 12]
    default_landmark = db.Column(db.String(150), nullable=True)[cite: 12]
    points_balance = db.Column(db.Float, default=0.0)[cite: 12]
    is_credit_eligible = db.Column(db.Boolean, default=False)[cite: 12]
    credit_limit = db.Column(db.Float, default=0.0)[cite: 12]
    outstanding_ar = db.Column(db.Float, default=0.0)[cite: 12]
    accumulated_spend = db.Column(db.Float, default=0.0)[cite: 12]
    card_number = db.Column(db.String(20), unique=True, nullable=True)[cite: 12]
    card_status = db.Column(db.String(20), default="ACTIVE")[cite: 12]
    card_expires_at = db.Column(db.Date, nullable=True)[cite: 12]
    referred_by = db.Column(db.String(50), nullable=True)[cite: 12]
    last_daily_login = db.Column(db.Date, nullable=True)[cite: 12]
    login_streak = db.Column(db.Integer, default=1)[cite: 12]
    wifi_voucher_code = db.Column(db.String(20), nullable=True)[cite: 12]
    wifi_minutes_left = db.Column(db.Integer, default=10)[cite: 12]
    last_active_at = db.Column(db.DateTime, default=datetime.utcnow)[cite: 12]
    created_at = db.Column(db.DateTime, default=datetime.utcnow)[cite: 12]

class DeliveryZone(db.Model):
    __tablename__ = 'delivery_zone'
    id = db.Column(db.Integer, primary_key=True)[cite: 12]
    place_name = db.Column(db.String(100), nullable=False)[cite: 12]
    barangay = db.Column(db.String(100), nullable=False)[cite: 12]
    rate = db.Column(db.Float, nullable=False)[cite: 12]
    distance = db.Column(db.String(50), nullable=True)[cite: 12]
    note = db.Column(db.String(150), nullable=True)[cite: 12]
    is_active = db.Column(db.Boolean, default=True)[cite: 12]

class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)[cite: 12]
    name = db.Column(db.String(80), unique=True, nullable=False)[cite: 12]

class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)[cite: 12]
    name = db.Column(db.String(120), nullable=False)[cite: 12]
    category_name = db.Column(db.String(80), nullable=False)[cite: 12]
    price = db.Column(db.Float, nullable=False)[cite: 12]
    cost = db.Column(db.Float, default=0.0, nullable=True)[cite: 12]
    stock = db.Column(db.Integer, default=100)[cite: 12]
    image_url = db.Column(db.Text, nullable=True)[cite: 12]
    is_featured = db.Column(db.Boolean, default=False)[cite: 12]
    is_top_seller = db.Column(db.Boolean, default=False)[cite: 12]
    is_active = db.Column(db.Boolean, default=True)[cite: 12]
    available_start_time = db.Column(db.String(10), nullable=True)[cite: 12]
    available_end_time = db.Column(db.String(10), nullable=True)[cite: 12]
    total_likes = db.Column(db.Integer, default=0)[cite: 12]
    comments = db.relationship('ProductComment', backref='product_rel', cascade="all, delete-orphan", lazy=True)[cite: 12]

class ProductLike(db.Model):
    __tablename__ = 'product_like'
    id = db.Column(db.Integer, primary_key=True)[cite: 12]
    product_id = db.Column(db.Integer, db.ForeignKey('product.id', ondelete='CASCADE'), nullable=False)[cite: 12]
    ip_address = db.Column(db.String(50), nullable=False)[cite: 12]
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id', ondelete='SET NULL'), nullable=True)[cite: 12]
    created_at = db.Column(db.DateTime, default=datetime.utcnow)[cite: 12]

class ProductComment(db.Model):
    __tablename__ = 'product_comment'
    id = db.Column(db.Integer, primary_key=True)[cite: 12]
    product_id = db.Column(db.Integer, db.ForeignKey('product.id', ondelete='CASCADE'), nullable=False)[cite: 12]
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id', ondelete='SET NULL'), nullable=True)[cite: 12]
    author_name = db.Column(db.String(100), nullable=False)[cite: 12]
    ip_address = db.Column(db.String(50), nullable=False)[cite: 12]
    comment_text = db.Column(db.Text, nullable=False)[cite: 12]
    created_at = db.Column(db.DateTime, default=datetime.utcnow)[cite: 12]

class Order(db.Model):
    __tablename__ = 'order'
    id = db.Column(db.Integer, primary_key=True)[cite: 12]
    order_type = db.Column(db.String(30), nullable=False)[cite: 12]
    dining_option = db.Column(db.String(20), default='DINE-IN')[cite: 12]
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)[cite: 12]
    customer_name = db.Column(db.String(100), default='Customer')[cite: 12]
    contact_number = db.Column(db.String(50), default='N/A')[cite: 12]
    fb_messenger = db.Column(db.String(150), nullable=True)[cite: 12]
    delivery_address = db.Column(db.Text, nullable=True)[cite: 12]
    landmark = db.Column(db.String(150), nullable=True)[cite: 12]
    pickup_time = db.Column(db.String(50), nullable=True)[cite: 12]
    target_time = db.Column(db.String(50), nullable=True)[cite: 12]
    change_for = db.Column(db.Float, nullable=True)[cite: 12]
    gcash_ref = db.Column(db.String(10), nullable=True)[cite: 12]
    subtotal = db.Column(db.Float, nullable=False)[cite: 12]
    delivery_fee = db.Column(db.Float, default=0.0)[cite: 12]
    total_amount = db.Column(db.Float, nullable=False)[cite: 12]
    payment_method = db.Column(db.String(20), nullable=False)[cite: 12]
    payment_verified = db.Column(db.Boolean, default=False)[cite: 12]
    status = db.Column(db.String(30), default="VERIFICATION")[cite: 12]
    is_unpaid = db.Column(db.Boolean, default=False)[cite: 12]
    collection_notes = db.Column(db.String(255), nullable=True)[cite: 12]
    notes = db.Column(db.Text, nullable=False, default="None")[cite: 12]
    created_at = db.Column(db.DateTime, default=datetime.utcnow)[cite: 12]
    customer = db.relationship('Customer', backref='orders', lazy=True)[cite: 12]
    items = db.relationship('OrderItem', backref='order_rel', cascade="all, delete-orphan", lazy=True)[cite: 12]

class OrderItem(db.Model):
    __tablename__ = 'order_item'
    id = db.Column(db.Integer, primary_key=True)[cite: 12]
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)[cite: 12]
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)[cite: 12]
    product_name = db.Column(db.String(120), nullable=False)[cite: 12]
    unit_price = db.Column(db.Float, nullable=False)[cite: 12]
    cost_price = db.Column(db.Float, default=0.0, nullable=True)[cite: 12]
    quantity = db.Column(db.Integer, nullable=False)[cite: 12]
    subtotal = db.Column(db.Float, nullable=False)[cite: 12]

class Expense(db.Model):
    __tablename__ = 'expense'
    id = db.Column(db.Integer, primary_key=True)[cite: 12]
    title = db.Column(db.String(150), nullable=False)[cite: 12]
    amount = db.Column(db.Float, nullable=False)[cite: 12]
    category = db.Column(db.String(50), default='General')[cite: 12]
    created_by = db.Column(db.String(50), nullable=True)[cite: 12]
    created_at = db.Column(db.DateTime, default=datetime.utcnow)[cite: 12]

class VaultDrop(db.Model):
    __tablename__ = 'vault_drop'
    id = db.Column(db.Integer, primary_key=True)[cite: 12]
    drop_number = db.Column(db.Integer, nullable=False)[cite: 12]
    amount = db.Column(db.Float, nullable=False)[cite: 12]
    notes = db.Column(db.String(255), nullable=True)[cite: 12]
    cash_breakdown = db.Column(db.Text, nullable=True)[cite: 12]
    created_by = db.Column(db.String(50), nullable=True)[cite: 12]
    created_at = db.Column(db.DateTime, default=datetime.utcnow)[cite: 12]

class ChangeFund(db.Model):
    __tablename__ = 'change_fund'
    id = db.Column(db.Integer, primary_key=True)[cite: 12]
    fund_title = db.Column(db.String(150), nullable=False, default="Cashier Opening Change Fund")[cite: 12]
    amount = db.Column(db.Float, nullable=False)[cite: 12]
    notes = db.Column(db.String(255), nullable=True)[cite: 12]
    created_by = db.Column(db.String(50), nullable=True)[cite: 12]
    created_at = db.Column(db.DateTime, default=datetime.utcnow)[cite: 12]

class RewardLedger(db.Model):
    __tablename__ = 'reward_ledger'
    id = db.Column(db.Integer, primary_key=True)[cite: 12]
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)[cite: 12]
    points_change = db.Column(db.Float, nullable=False)[cite: 12]
    reason = db.Column(db.String(150), nullable=False)[cite: 12]
    created_at = db.Column(db.DateTime, default=datetime.utcnow)[cite: 12]

class SiteVisitor(db.Model):
    __tablename__ = 'site_visitor'
    id = db.Column(db.Integer, primary_key=True)[cite: 12]
    ip_address = db.Column(db.String(50), unique=True, nullable=False)[cite: 12]
    visit_count = db.Column(db.Integer, default=1)[cite: 12]
    visited_at = db.Column(db.DateTime, default=datetime.utcnow)[cite: 12]

class PromotionTracker(db.Model):
    __tablename__ = 'promotion_tracker'
    id = db.Column(db.Integer, primary_key=True)[cite: 12]
    promo_code = db.Column(db.String(50), unique=True, nullable=False)[cite: 12]
    title = db.Column(db.String(120), nullable=False)[cite: 12]
    promo_price = db.Column(db.Float, nullable=False)[cite: 12]
    promo_cost = db.Column(db.Float, default=0.0, nullable=True)[cite: 12]
    page_views = db.Column(db.Integer, default=0)[cite: 12]
    claims_count = db.Column(db.Integer, default=0)[cite: 12]
    total_revenue = db.Column(db.Float, default=0.0)[cite: 12]
    is_active = db.Column(db.Boolean, default=True)[cite: 12]
    is_visible = db.Column(db.Boolean, default=True)[cite: 12]
    created_at = db.Column(db.DateTime, default=datetime.utcnow)[cite: 12]

# ==================== PWA ROOT ROUTES ====================

@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'manifest.json', mimetype='application/manifest+json')[cite: 12]

@app.route('/sw.js')
def serve_sw():
    response = send_from_directory(os.path.join(app.root_path, 'static'), 'sw.js', mimetype='application/javascript')[cite: 12]
    response.headers['Service-Worker-Allowed'] = '/'[cite: 12]
    return response[cite: 12]

# ==================== SAFE MIGRATION & RUN HOOKS ====================

def run_db_setup():
    global _DB_INITIALIZED
    if _DB_INITIALIZED:
        return
    try:
        db.create_all()[cite: 12]
        
        cols = [
            ("customer", "last_daily_login", "DATE"),
            ("customer", "login_streak", "INTEGER DEFAULT 1"),
            ("customer", "referred_by", "VARCHAR(50)"),
            ("customer", "last_active_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ("order", "dining_option", "VARCHAR(20) DEFAULT 'DINE-IN'"),
            ("promotion_tracker", "is_visible", "BOOLEAN DEFAULT TRUE"),
            ("product", "cost", "FLOAT DEFAULT 0.0"),
            ("product", "available_start_time", "VARCHAR(10)"),
            ("product", "available_end_time", "VARCHAR(10)"),
            ("vault_drop", "cash_breakdown", "TEXT")
        ]

        with db.engine.connect() as conn:
            for tbl, col, col_type in cols:
                try:
                    table_name = f'"{tbl}"' if tbl == "order" else tbl
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col} {col_type};"))
                    conn.commit()
                except Exception:
                    pass

        default_roles = [('admin', '1234', 'ADMIN'), ('cashier1', '1111', 'CASHIER')][cite: 12]
        for user, pin, role in default_roles:
            st = Staff.query.filter_by(username=user).first()[cite: 12]
            if not st:
                db.session.add(Staff(username=user, pin_hash=generate_password_hash(pin), role=role))[cite: 12]
            else:
                st.pin_hash = generate_password_hash(pin)[cite: 12]
                st.role = role[cite: 12]
        db.session.commit()[cite: 12]
        ensure_default_promos()[cite: 12]
        _DB_INITIALIZED = True
    except Exception:
        db.session.rollback()[cite: 12]

@app.before_request
def app_startup_and_session_handler():
    session.permanent = True
    if not _DB_INITIALIZED:
        run_db_setup()

    if 'customer_id' in session:
        try:
            cust = Customer.query.get(session['customer_id'])[cite: 12]
            if cust and hasattr(cust, 'last_active_at'):
                cust.last_active_at = datetime.utcnow()[cite: 12]
                db.session.commit()[cite: 12]
        except Exception:
            db.session.rollback()[cite: 12]

# ==================== HELPERS & GUARDS ====================

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()[cite: 12]
    return request.remote_addr or '127.0.0.1'[cite: 12]

def get_store_settings():
    try:
        settings = {s.key: s.value for s in StoreSetting.query.all()}[cite: 12]
    except Exception:
        settings = {}[cite: 12]
    defaults = {
        'store_open_time': '08:00',
        'store_close_time': '21:00',
        'delivery_open_time': '08:00',
        'delivery_close_time': '20:00',
        'is_store_open': 'true',
        'is_delivery_enabled': 'true'
    }[cite: 12]
    for k, v in defaults.items():
        settings.setdefault(k, v)[cite: 12]
    return settings[cite: 12]

def check_operating_status():
    s = get_store_settings()[cite: 12]
    now_utc = datetime.utcnow()[cite: 12]
    now_ph = (now_utc + timedelta(hours=8)).time()[cite: 12]

    def parse_t(val, fallback):
        try:
            return datetime.strptime(val, '%H:%M').time()[cite: 12]
        except Exception:
            return fallback[cite: 12]

    store_open = parse_t(s.get('store_open_time', '08:00'), time(8, 0))[cite: 12]
    store_close = parse_t(s.get('store_close_time', '21:00'), time(21, 0))[cite: 12]
    del_open = parse_t(s.get('delivery_open_time', '08:00'), time(8, 0))[cite: 12]
    del_close = parse_t(s.get('delivery_close_time', '20:00'), time(20, 0))[cite: 12]

    is_store_active = (s.get('is_store_open') == 'true') and (store_open <= now_ph <= store_close)[cite: 12]
    is_delivery_active = (s.get('is_delivery_enabled') == 'true') and (del_open <= now_ph <= del_close) and is_store_active[cite: 12]

    return {
        'store_open': is_store_active,
        'delivery_open': is_delivery_active,
        'settings': s,
        'current_time': now_ph.strftime('%I:%M %p')
    }[cite: 12]

def is_product_available_now(prod):
    if not prod.is_active:
        return False[cite: 12]
    if not getattr(prod, 'available_start_time', None) or not getattr(prod, 'available_end_time', None):
        return True[cite: 12]
    try:
        now_ph = (datetime.utcnow() + timedelta(hours=8)).time()[cite: 12]
        start = datetime.strptime(prod.available_start_time, '%H:%M').time()[cite: 12]
        end = datetime.strptime(prod.available_end_time, '%H:%M').time()[cite: 12]
        if start <= end:
            return start <= now_ph <= end[cite: 12]
        return now_ph >= start or now_ph <= end[cite: 12]
    except Exception:
        return True[cite: 12]

def ensure_default_promos():
    try:
        deal1 = PromotionTracker.query.filter_by(promo_code='BURGER_FRIES_50').first()[cite: 12]
        if not deal1:
            db.session.add(PromotionTracker(
                promo_code='BURGER_FRIES_50',
                title='1 Regular Burger + Crispy Fries',
                promo_price=50.0,
                page_views=0,
                claims_count=0,
                total_revenue=0.0,
                is_active=True,
                is_visible=True
            ))[cite: 12]

        deal2 = PromotionTracker.query.filter_by(promo_code='BEEFY_NACHOS_75').first()[cite: 12]
        if not deal2:
            db.session.add(PromotionTracker(
                promo_code='BEEFY_NACHOS_75',
                title='All-New Loaded Beefy Nachos Supreme',
                promo_price=75.0,
                page_views=0,
                claims_count=0,
                total_revenue=0.0,
                is_active=True,
                is_visible=True
            ))[cite: 12]

        db.session.commit()[cite: 12]
    except Exception:
        db.session.rollback()[cite: 12]

@app.context_processor
def inject_globals():
    try:
        setting = StoreSetting.query.filter_by(key='logo_url').first()[cite: 12]
        logo = setting.value if setting else '/static/logo.png'[cite: 12]
    except Exception:
        logo = '/static/logo.png'[cite: 12]
    status = check_operating_status()[cite: 12]
    return dict(store_logo=logo, status=status)[cite: 12]

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_user'):
            return redirect(url_for('staff_login', target='admin'))[cite: 12]
        return f(*args, **kwargs)[cite: 12]
    return decorated[cite: 12]

def require_cashier(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not (session.get('cashier_user') or session.get('admin_user')):
            return redirect(url_for('staff_login', target='cashier'))[cite: 12]
        return f(*args, **kwargs)[cite: 12]
    return decorated[cite: 12]

# ==================== REAL-TIME POLLING API ====================

@app.route('/api/queue-counts')
def api_queue_counts():
    try:
        pending_cashier = Order.query.filter_by(status="VERIFICATION").count()
    except Exception:
        pending_cashier = 0
    return jsonify({'pending_cashier': pending_cashier})

# ==================== STOREFRONT ====================

@app.route('/')
def store_catalog():
    try:
        ip = get_client_ip()[cite: 12]
        v = SiteVisitor.query.filter_by(ip_address=ip).first()[cite: 12]
        if not v:
            db.session.add(SiteVisitor(ip_address=ip, visit_count=1))[cite: 12]
        else:
            v.visit_count = (v.visit_count or 0) + 1[cite: 12]
        db.session.commit()[cite: 12]
    except Exception:
        db.session.rollback()[cite: 12]

    try:
        unique_visitors = SiteVisitor.query.count()
        total_accumulated_visits = db.session.query(db.func.coalesce(db.func.sum(SiteVisitor.visit_count), 0)).scalar() or unique_visitors
    except Exception:
        unique_visitors = 1
        total_accumulated_visits = 1

    categories = Category.query.all()[cite: 12]
    all_active_products = Product.query.filter_by(is_active=True).all()[cite: 12]
    available_products = [p for p in all_active_products if is_product_available_now(p)][cite: 12]

    featured = [p for p in available_products if p.is_featured][cite: 12]
    top_sellers = [p for p in available_products if p.is_top_seller][cite: 12]
    products = sorted(available_products, key=lambda x: (-(x.total_likes or 0), x.id))[cite: 12]

    liked_ids = {pl.product_id for pl in ProductLike.query.filter_by(ip_address=get_client_ip()).all()}[cite: 12]
    delivery_zones = DeliveryZone.query.filter_by(is_active=True).all()[cite: 12]
    status = check_operating_status()[cite: 12]
    active_promos = PromotionTracker.query.filter_by(is_active=True, is_visible=True).all()[cite: 12]

    try:
        top_customers = Customer.query.order_by(Customer.points_balance.desc()).limit(10).all()
    except Exception:
        top_customers = []

    cust = None
    if 'customer_id' in session:
        cust = Customer.query.get(session['customer_id'])[cite: 12]

    return render_template('store_catalog.html', 
                           categories=categories, 
                           featured=featured, 
                           top_sellers=top_sellers, 
                           products=products, 
                           liked_ids=liked_ids, 
                           delivery_zones=delivery_zones, 
                           active_promos=active_promos, 
                           top_customers=top_customers, 
                           cust=cust, 
                           status=status, 
                           unique_visitors=unique_visitors, 
                           total_accumulated_visits=total_accumulated_visits)[cite: 4]

@app.route('/promo/burger-deal')
def promo_burger_deal():
    promo = PromotionTracker.query.filter_by(promo_code='BURGER_FRIES_50').first()[cite: 12]
    if promo:
        promo.page_views = (promo.page_views or 0) + 1[cite: 12]
        db.session.commit()[cite: 12]
    return render_template('promo_burger_deal.html')[cite: 12]

@app.route('/promo/beefy-nachos')
def promo_beefy_nachos():
    promo = PromotionTracker.query.filter_by(promo_code='BEEFY_NACHOS_75').first()[cite: 12]
    if promo:
        promo.page_views = (promo.page_views or 0) + 1[cite: 12]
        db.session.commit()[cite: 12]
    return render_template('promo_beefy_nachos.html')[cite: 12]

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    prod = Product.query.get_or_404(product_id)[cite: 12]
    ip = get_client_ip()[cite: 12]
    liked = bool(ProductLike.query.filter_by(product_id=product_id, ip_address=ip).first())[cite: 12]
    return render_template('product_detail.html', prod=prod, liked=liked)[cite: 12]

@app.route('/api/toggle-like/<int:product_id>', methods=['POST'])
def api_toggle_like(product_id):
    ip = get_client_ip()[cite: 12]
    cust_id = session.get('customer_id')[cite: 12]
    prod = Product.query.get_or_404(product_id)[cite: 12]

    existing = ProductLike.query.filter_by(product_id=product_id, ip_address=ip).first()[cite: 12]
    if existing:
        db.session.delete(existing)[cite: 12]
        prod.total_likes = max(0, (prod.total_likes or 0) - 1)[cite: 12]
        db.session.commit()[cite: 12]
        return jsonify({'liked': False, 'total_likes': prod.total_likes})[cite: 12]
    else:
        db.session.add(ProductLike(product_id=product_id, ip_address=ip, customer_id=cust_id))[cite: 12]
        prod.total_likes = (prod.total_likes or 0) + 1[cite: 12]
        db.session.commit()[cite: 12]
        return jsonify({'liked': True, 'total_likes': prod.total_likes})[cite: 12]

@app.route('/api/add-comment/<int:product_id>', methods=['POST'])
def api_add_comment(product_id):
    ip = get_client_ip()[cite: 12]
    cust_id = session.get('customer_id')[cite: 12]
    data = request.get_json() or {}[cite: 12]
    text_content = data.get('comment', '').strip()[cite: 12]
    if not text_content:
        return jsonify({'success': False, 'message': 'Comment cannot be empty.'}), 400[cite: 12]

    name = f"Guest ({ip})"[cite: 12]
    if cust_id:
        cust = Customer.query.get(cust_id)[cite: 12]
        if cust:
            name = cust.name[cite: 12]

    comment = ProductComment(product_id=product_id, customer_id=cust_id, author_name=name, ip_address=ip, comment_text=text_content)[cite: 12]
    db.session.add(comment)[cite: 12]
    db.session.commit()[cite: 12]
    return jsonify({'success': True, 'author': name, 'comment': text_content, 'created_at': 'Just now'})[cite: 12]

@app.route('/api/storefront-checkout', methods=['POST'])
def api_storefront_checkout():
    if 'customer_id' not in session:
        return jsonify({'success': False, 'message': 'Registration / Login is required. No guest checkout.'}), 403[cite: 12]

    status = check_operating_status()[cite: 12]
    cust = Customer.query.get(session['customer_id'])[cite: 12]
    data = request.get_json() or {}[cite: 12]
    items = data.get('items', [])[cite: 12]
    order_type = data.get('order_type', 'PICKUP').upper()[cite: 12]
    dining_opt = data.get('dining_option', 'TAKEOUT').upper()[cite: 12]
    pay_method = data.get('payment_method', 'CASH').upper()[cite: 12]
    notes = data.get('notes', '').strip() or 'None'[cite: 12]
    target_time = data.get('target_time', '').strip()[cite: 12]
    zone_id = data.get('delivery_zone_id')[cite: 12]
    landmark = data.get('landmark', '').strip()[cite: 12]
    delivery_address = data.get('delivery_address', '').strip()[cite: 12]
    gcash_ref = data.get('gcash_ref', '').strip()[cite: 12]
    fb = data.get('fb_messenger', '').strip()[cite: 12]

    if order_type == 'PICKUP' and not status['store_open']:
        return jsonify({'success': False, 'message': 'Store ordering is currently closed.'}), 400[cite: 12]

    if order_type == 'DELIVERY' and not status['delivery_open']:
        return jsonify({'success': False, 'message': 'Barangay delivery is currently unavailable/closed.'}), 400[cite: 12]

    if not items or not target_time:
        return jsonify({'success': False, 'message': 'Please complete your target time and select cart items.'}), 400[cite: 12]

    delivery_fee = 0.0[cite: 12]
    final_address = delivery_address[cite: 12]
    final_landmark = landmark[cite: 12]

    if order_type == 'DELIVERY':
        dining_opt = 'DELIVERY'[cite: 12]
        if not zone_id and (not landmark or not delivery_address):
            return jsonify({'success': False, 'message': 'Please choose a Barangay Delivery Zone or provide address info.'}), 400[cite: 12]
        if zone_id:
            zone = DeliveryZone.query.get(zone_id)[cite: 12]
            if zone:
                delivery_fee = zone.rate[cite: 12]
                final_address = f"Barangay: {zone.barangay} ({zone.place_name})"[cite: 12]
                final_landmark = landmark or zone.note or "Designated Delivery Spot"[cite: 12]

    if pay_method == 'CREDIT' and not cust.is_credit_eligible:
        return jsonify({'success': False, 'message': 'Your account is not authorized for A/R Credit.'}), 403[cite: 12]

    if pay_method in ['GCASH', 'CREDIT'] and not fb:
        return jsonify({'success': False, 'message': 'Facebook messenger link is required for evaluation.'}), 400[cite: 12]

    if pay_method == 'GCASH' and len(gcash_ref) < 6:
        return jsonify({'success': False, 'message': 'Please input the 6-digit GCash Reference Number.'}), 400[cite: 12]

    subtotal = sum(Product.query.get(it['product_id']).price * int(it['quantity']) for it in items if Product.query.get(it['product_id']))[cite: 12]
    total = subtotal + delivery_fee[cite: 12]

    order = Order(
        order_type=order_type,
        dining_option=dining_opt,
        customer_id=cust.id,
        customer_name=cust.name,
        contact_number=cust.contact,
        fb_messenger=fb,
        delivery_address=final_address if order_type == 'DELIVERY' else None,
        landmark=final_landmark if order_type == 'DELIVERY' else None,
        pickup_time=target_time if order_type == 'PICKUP' else None,
        target_time=target_time,
        change_for=float(data.get('change_for') or 0.0) if pay_method in ['CASH', 'COD'] else None,
        gcash_ref=gcash_ref if pay_method == 'GCASH' else None,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        total_amount=total,
        payment_method=pay_method,
        payment_verified=False,
        status='VERIFICATION',
        notes=notes
    )[cite: 12]
    db.session.add(order)[cite: 12]
    db.session.flush()[cite: 12]

    for it in items:
        prod = Product.query.get(it['product_id'])[cite: 12]
        if prod:
            db.session.add(OrderItem(
                order_id=order.id, product_id=prod.id, product_name=prod.name,
                unit_price=prod.price, quantity=int(it['quantity']),
                subtotal=prod.price * int(it['quantity'])
            ))[cite: 12]
            if prod.stock >= int(it['quantity']):
                prod.stock -= int(it['quantity'])[cite: 12]

    db.session.commit()[cite: 12]
    return jsonify({'success': True, 'order_id': order.id, 'total': total})[cite: 12]

# ==================== TABLET KIOSK ENDPOINTS ====================

@app.route('/tablet')
def tablet_kiosk():
    categories = Category.query.all()[cite: 12]
    all_active_products = Product.query.filter_by(is_active=True).all()[cite: 12]
    available_products = [p for p in all_active_products if is_product_available_now(p)][cite: 12]
    return render_template('tablet.html', categories=categories, products=available_products)[cite: 12]

@app.route('/api/tablet-checkout', methods=['POST'])
def api_tablet_checkout():
    data = request.get_json() or {}[cite: 12]
    items = data.get('items', [])[cite: 12]
    dining_opt = data.get('dining_option', 'DINE-IN').upper()[cite: 12]
    customer_name = data.get('customer_name', 'Tablet Kiosk Guest').strip() or 'Tablet Kiosk Guest'[cite: 12]
    pay_method = data.get('payment_method', 'CASH').upper()[cite: 12]
    notes = data.get('notes', 'Tablet Self-Order').strip() or 'Tablet Self-Order'[cite: 12]

    if not items:
        return jsonify({'success': False, 'message': 'Ticket is empty.'}), 400[cite: 12]

    cust_id = None[cite: 12]
    contact_num = 'Kiosk'[cite: 12]
    if 'PIN:' in customer_name:
        pin_code = customer_name.split('PIN:')[1].replace(')', '').strip()[cite: 12]
        matched = Customer.query.filter((Customer.contact == pin_code) | (Customer.card_number == pin_code)).first()[cite: 12]
        if matched:
            cust_id = matched.id[cite: 12]
            customer_name = matched.name[cite: 12]
            contact_num = matched.contact[cite: 12]

    subtotal = sum(Product.query.get(it['product_id']).price * int(it['quantity']) for it in items if Product.query.get(it['product_id']))[cite: 12]

    order = Order(
        order_type='TABLET',
        dining_option=dining_opt,
        customer_id=cust_id,
        customer_name=customer_name,
        contact_number=contact_num,
        subtotal=subtotal,
        delivery_fee=0.0,
        total_amount=subtotal,
        payment_method=pay_method,
        payment_verified=False,
        status='VERIFICATION',
        notes=notes
    )[cite: 12]
    db.session.add(order)[cite: 12]
    db.session.flush()[cite: 12]

    for it in items:
        prod = Product.query.get(it['product_id'])[cite: 12]
        if prod:
            db.session.add(OrderItem(
                order_id=order.id,
                product_id=prod.id,
                product_name=prod.name,
                unit_price=prod.price,
                quantity=int(it['quantity']),
                subtotal=prod.price * int(it['quantity'])
            ))[cite: 12]
            if prod.stock >= int(it['quantity']):
                prod.stock -= int(it['quantity'])[cite: 12]

    db.session.commit()[cite: 12]
    return jsonify({'success': True, 'order_id': order.id, 'total': subtotal})[cite: 12]

# ==================== CASHIER TERMINAL & CLAIM DISPATCH ====================

@app.route('/pos/cashier')
@require_cashier
def cashier_terminal():
    categories = Category.query.all()[cite: 12]
    products = Product.query.filter_by(is_active=True).all()[cite: 12]
    
    try:
        pending_orders = Order.query.filter_by(status="VERIFICATION").order_by(Order.created_at.asc()).all()
    except Exception:
        pending_orders = []
        
    try:
        completed_orders = Order.query.filter_by(status="COMPLETED").order_by(Order.created_at.desc()).limit(15).all()
    except Exception:
        completed_orders = []
        
    try:
        unpaid_collections = Order.query.filter_by(is_unpaid=True).order_by(Order.created_at.desc()).all()
    except Exception:
        unpaid_collections = []
        
    staff_list = Staff.query.all()[cite: 12]
    customers_list = Customer.query.order_by(Customer.name.asc()).all()[cite: 12]

    two_mins_ago = datetime.utcnow() - timedelta(minutes=2)[cite: 12]
    try:
        online_customers = Customer.query.filter(Customer.last_active_at >= two_mins_ago).order_by(Customer.last_active_at.desc()).all()
    except Exception:
        online_customers = [][cite: 12]

    try:
        credit_customers = Customer.query.filter(Customer.outstanding_ar > 0).order_by(Customer.outstanding_ar.desc()).all()
    except Exception:
        credit_customers = []

    today = date.today()
    start_today = datetime.combine(today, time.min)
    end_today = datetime.combine(today, time.max)
    
    try:
        today_expenses = Expense.query.filter(Expense.created_at >= start_today, Expense.created_at <= end_today).order_by(Expense.created_at.desc()).all()
    except Exception:
        today_expenses = []

    try:
        today_drops = VaultDrop.query.filter(VaultDrop.created_at >= start_today, VaultDrop.created_at <= end_today).order_by(VaultDrop.drop_number.asc()).all()
    except Exception:
        today_drops = []

    try:
        today_change_funds = ChangeFund.query.filter(ChangeFund.created_at >= start_today, ChangeFund.created_at <= end_today).order_by(ChangeFund.created_at.desc()).all()
    except Exception:
        today_change_funds = []
        
    next_drop_num = len(today_drops) + 1[cite: 12]

    return render_template('cashier_pos.html', 
                           categories=categories, 
                           products=products, 
                           pending_orders=pending_orders, 
                           completed_orders=completed_orders, 
                           unpaid_collections=unpaid_collections, 
                           credit_customers=credit_customers, 
                           online_customers=online_customers, 
                           staff_list=staff_list, 
                           customers_list=customers_list, 
                           today_expenses=today_expenses, 
                           today_drops=today_drops, 
                           today_change_funds=today_change_funds, 
                           next_drop_num=next_drop_num)[cite: 11]

@app.route('/pos/topup-member-wifi', methods=['POST'])
@require_cashier
def cashier_topup_member_wifi():
    cust_id = request.form.get('customer_id')[cite: 12]
    if not cust_id:
        flash("Please select a member.", "error")[cite: 12]
        return redirect(url_for('cashier_terminal'))[cite: 12]
    
    cust = Customer.query.get_or_404(int(cust_id))[cite: 12]
    cust.wifi_minutes_left = (cust.wifi_minutes_left or 0) + 10[cite: 12]
    if not cust.wifi_voucher_code:
        cust.wifi_voucher_code = "MFH-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))[cite: 12]
    
    db.session.commit()[cite: 12]
    flash(f"📶 Stacked +10 Mins Wi-Fi for {cust.name}! (Total: {cust.wifi_minutes_left} mins)", "success")[cite: 12]
    return redirect(url_for('cashier_terminal'))[cite: 12]

@app.route('/pos/direct-sale', methods=['POST'])
@require_cashier
def cashier_direct_sale():
    data = request.get_json() or {}[cite: 12]
    items = data.get('items', [])[cite: 12]
    cust_type = data.get('customer_type', 'WALKIN')[cite: 12]
    reg_id = data.get('registered_customer_id')[cite: 12]
    dining_opt = data.get('dining_option', 'DINE-IN').upper()[cite: 12]
    pay_method = data.get('payment_method', 'CASH').upper()[cite: 12]
    cust_name = data.get('customer_name', 'Counter Walk-in').strip() or 'Counter Walk-in'[cite: 12]
    notes = data.get('notes', 'Cashier Counter POS Sale').strip() or 'Cashier Counter POS Sale'[cite: 12]
    change_for = float(data.get('change_for') or 0.0)[cite: 12]

    if not items:
        return jsonify({'success': False, 'message': 'No items in cart.'}), 400[cite: 12]

    subtotal = sum(Product.query.get(it['product_id']).price * int(it['quantity']) for it in items if Product.query.get(it['product_id']))[cite: 12]

    cust_id = None[cite: 12]
    contact = 'N/A'[cite: 12]
    points_earned = 0[cite: 12]

    if cust_type == 'REGISTERED' and reg_id:
        cust = Customer.query.get(reg_id)[cite: 12]
        if cust:
            cust_id = cust.id[cite: 12]
            cust_name = cust.name[cite: 12]
            contact = cust.contact[cite: 12]
            cust.accumulated_spend = (cust.accumulated_spend or 0.0) + subtotal[cite: 12]
            points_earned = int(subtotal // 30)[cite: 12]
            if points_earned > 0:
                cust.points_balance = (cust.points_balance or 0.0) + points_earned[cite: 12]
                db.session.add(RewardLedger(
                    customer_id=cust.id,
                    points_change=points_earned,
                    reason=f"Counter POS Sale (₱{subtotal:,.2f})"
                ))[cite: 12]

    order = Order(
        order_type='COUNTER_SALE',
        dining_option=dining_opt,
        customer_id=cust_id,
        customer_name=cust_name,
        contact_number=contact,
        subtotal=subtotal,
        delivery_fee=0.0,
        total_amount=subtotal,
        payment_method=pay_method,
        payment_verified=True,
        change_for=change_for if change_for > 0 else None,
        status='COMPLETED',
        notes=notes
    )[cite: 12]
    db.session.add(order)[cite: 12]
    db.session.flush()[cite: 12]

    for it in items:
        prod = Product.query.get(it['product_id'])[cite: 12]
        if prod:
            db.session.add(OrderItem(
                order_id=order.id,
                product_id=prod.id,
                product_name=prod.name,
                unit_price=prod.price,
                cost_price=0.0,
                quantity=int(it['quantity']),
                subtotal=prod.price * int(it['quantity'])
            ))[cite: 12]
            if prod.stock >= int(it['quantity']):
                prod.stock -= int(it['quantity'])[cite: 12]

    db.session.commit()[cite: 12]
    return jsonify({
        'success': True,
        'order_id': order.id,
        'total': subtotal,
        'points_earned': points_earned
    })[cite: 12]

@app.route('/pos/claim-promo', methods=['POST'])
@require_cashier
def cashier_claim_promo():
    promo_code = request.form.get('promo_code', 'BURGER_FRIES_50')[cite: 12]
    reg_id = request.form.get('registered_customer_id')[cite: 12]
    dining_opt = request.form.get('dining_option', 'DINE-IN').upper()[cite: 12]
    pay_method = request.form.get('payment_method', 'CASH').upper()[cite: 12]
    
    promo = PromotionTracker.query.filter_by(promo_code=promo_code).first()[cite: 12]
    if not promo:
        flash("Promotion deal not found.", "error")[cite: 12]
        return redirect(url_for('cashier_terminal'))[cite: 12]

    cust_id = None[cite: 12]
    cust_name = 'Walk-in Member'[cite: 12]
    contact = 'N/A'[cite: 12]
    points_earned = 0[cite: 12]

    if reg_id:
        cust = Customer.query.get(reg_id)[cite: 12]
        if cust:
            cust_id = cust.id[cite: 12]
            cust_name = cust.name[cite: 12]
            contact = cust.contact[cite: 12]
            cust.accumulated_spend = (cust.accumulated_spend or 0.0) + promo.promo_price[cite: 12]
            points_earned = int(promo.promo_price // 30)[cite: 12]
            if points_earned > 0:
                cust.points_balance = (cust.points_balance or 0.0) + points_earned[cite: 12]
                db.session.add(RewardLedger(
                    customer_id=cust.id,
                    points_change=points_earned,
                    reason=f"Promo Deal: {promo.title} (₱{promo.promo_price:,.2f})"
                ))[cite: 12]

    order = Order(
        order_type='PROMO_DEAL',
        dining_option=dining_opt,
        customer_id=cust_id,
        customer_name=cust_name,
        contact_number=contact,
        subtotal=promo.promo_price,
        delivery_fee=0.0,
        total_amount=promo.promo_price,
        payment_method=pay_method,
        payment_verified=True,
        status='COMPLETED',
        notes=f"[PROMO:{promo.promo_code}] {promo.title}"
    )[cite: 12]
    db.session.add(order)[cite: 12]
    db.session.flush()[cite: 12]

    db.session.add(OrderItem(
        order_id=order.id,
        product_id=None,
        product_name=f"[PROMO] {promo.title}",
        unit_price=promo.promo_price,
        cost_price=0.0,
        quantity=1,
        subtotal=promo.promo_price
    ))[cite: 12]

    promo.claims_count = (promo.claims_count or 0) + 1[cite: 12]
    promo.total_revenue = (promo.total_revenue or 0.0) + promo.promo_price[cite: 12]

    db.session.commit()[cite: 12]
    flash(f"🎉 Promo Deal '{promo.title}' recorded ({dining_opt}) for {cust_name} (₱{promo.promo_price:,.2f})!", "success")[cite: 12]
    return redirect(url_for('cashier_terminal'))[cite: 12]

@app.route('/pos/create-reservation', methods=['POST'])
@require_cashier
def cashier_create_reservation():
    cust_type = request.form.get('customer_type', 'REGISTERED')[cite: 12]
    reg_id = request.form.get('registered_customer_id')[cite: 12]
    product_id = request.form.get('product_id')[cite: 12]
    qty = int(request.form.get('quantity') or 1)[cite: 12]
    dining_opt = request.form.get('dining_option', 'TAKEOUT').upper()[cite: 12]
    target_time = request.form.get('target_time', '').strip() or 'Today'[cite: 12]
    pay_method = request.form.get('payment_method', 'CASH').upper()[cite: 12]
    notes = request.form.get('notes', '').strip() or 'In-Store Reservation'[cite: 12]

    if not product_id or qty <= 0:
        flash("Please select a valid product and quantity.", "error")[cite: 12]
        return redirect(url_for('cashier_terminal'))[cite: 12]

    prod = Product.query.get_or_404(int(product_id))[cite: 12]
    subtotal = prod.price * qty[cite: 12]

    cust_id = None[cite: 12]
    cust_name = 'Walk-in Guest'[cite: 12]
    contact = 'N/A'[cite: 12]

    if cust_type == 'REGISTERED' and reg_id:
        cust = Customer.query.get(int(reg_id))[cite: 12]
        if cust:
            cust_id = cust.id[cite: 12]
            cust_name = cust.name[cite: 12]
            contact = cust.contact[cite: 12]
    else:
        cust_name = request.form.get('custom_customer_name', '').strip() or 'Walk-in Reservation'[cite: 12]
        contact = request.form.get('custom_contact', '').strip() or 'N/A'[cite: 12]

    order = Order(
        order_type='RESERVATION',
        dining_option=dining_opt,
        customer_id=cust_id,
        customer_name=f"{cust_name} (Reserved: {target_time})",
        contact_number=contact,
        pickup_time=target_time,
        target_time=target_time,
        subtotal=subtotal,
        delivery_fee=0.0,
        total_amount=subtotal,
        payment_method=pay_method,
        payment_verified=False,
        status='VERIFICATION',
        notes=f"[{dining_opt} - RESERVED for {target_time}] {notes}"
    )[cite: 12]
    db.session.add(order)[cite: 12]
    db.session.flush()[cite: 12]

    db.session.add(OrderItem(
        order_id=order.id,
        product_id=prod.id,
        product_name=prod.name,
        unit_price=prod.price,
        cost_price=0.0,
        quantity=qty,
        subtotal=subtotal
    ))[cite: 12]

    if prod.stock >= qty:
        prod.stock -= qty[cite: 12]

    db.session.commit()[cite: 12]
    flash(f"📌 Reserved {prod.name} x{qty} ({dining_opt}) for {cust_name} (Pickup: {target_time}) — ₱{subtotal:,.2f}", "success")[cite: 12]
    return redirect(url_for('cashier_terminal'))[cite: 12]

@app.route('/pos/misc-sale', methods=['POST'])
@require_cashier
def cashier_misc_sale():
    service_name = request.form.get('service_name', '').strip() or 'Printing / Custom Service'[cite: 12]
    amount = float(request.form.get('amount') or 0.0)[cite: 12]
    pay_method = request.form.get('payment_method', 'CASH')[cite: 12]
    notes = request.form.get('notes', '').strip() or 'Over-the-counter Misc Service'[cite: 12]
    reg_cust_id = request.form.get('registered_customer_id')[cite: 12]
    custom_name = request.form.get('custom_customer_name', '').strip()[cite: 12]

    if amount <= 0:
        flash("Amount must be greater than zero.", "error")[cite: 12]
        return redirect(url_for('cashier_terminal'))[cite: 12]

    cust_id = None[cite: 12]
    customer_name = 'Walk-in Customer'[cite: 12]
    contact = 'N/A'[cite: 12]

    if reg_cust_id:
        cust = Customer.query.get(reg_cust_id)[cite: 12]
        if cust:
            cust_id = cust.id[cite: 12]
            customer_name = cust.name[cite: 12]
            contact = cust.contact[cite: 12]
            cust.accumulated_spend = (cust.accumulated_spend or 0.0) + amount[cite: 12]
            earned = int(amount // 30)[cite: 12]
            if earned > 0:
                cust.points_balance = (cust.points_balance or 0.0) + earned[cite: 12]
                db.session.add(RewardLedger(customer_id=cust.id, points_change=earned, reason=f"Service Purchase: {service_name}"))[cite: 12]
    elif custom_name:
        customer_name = custom_name[cite: 12]

    order = Order(
        order_type='SERVICE/MISC',
        dining_option='SERVICE',
        customer_id=cust_id,
        customer_name=customer_name,
        contact_number=contact,
        subtotal=amount,
        delivery_fee=0.0,
        total_amount=amount,
        payment_method=pay_method,
        payment_verified=True,
        status='COMPLETED',
        notes=notes
    )[cite: 12]
    db.session.add(order)[cite: 12]
    db.session.flush()[cite: 12]

    db.session.add(OrderItem(
        order_id=order.id,
        product_id=None,
        product_name=f"[Service] {service_name}",
        unit_price=amount,
        cost_price=0.0,
        quantity=1,
        subtotal=amount
    ))[cite: 12]

    db.session.commit()[cite: 12]
    flash(f"Misc Sale recorded: {service_name} for {customer_name} (₱{amount:,.2f})", "success")[cite: 12]
    return redirect(url_for('cashier_terminal'))[cite: 12]

@app.route('/pos/record-change-fund', methods=['POST'])
@require_cashier
def cashier_record_change_fund():
    title = request.form.get('fund_title', 'Opening Petty/Change Fund').strip()[cite: 12]
    amount = float(request.form.get('amount') or 0.0)[cite: 12]
    notes = request.form.get('notes', 'Ulam / Register Drawer Starting Cash').strip()[cite: 12]
    staff_user = session.get('cashier_user') or session.get('admin_user') or 'Cashier'[cite: 12]

    if amount <= 0:
        flash("Change fund amount must be greater than zero.", "error")[cite: 12]
        return redirect(url_for('cashier_terminal'))[cite: 12]

    db.session.add(ChangeFund(fund_title=title, amount=amount, notes=notes, created_by=staff_user))[cite: 12]
    db.session.commit()[cite: 12]
    flash(f"Change Fund (₱{amount:,.2f}) added to register drawer notes.", "success")[cite: 12]
    return redirect(url_for('cashier_terminal'))[cite: 12]

@app.route('/pos/create-collection', methods=['POST'])
@require_cashier
def cashier_create_collection():
    cust_type = request.form.get('customer_type', 'REGISTERED')[cite: 12]
    item_choice_type = request.form.get('item_choice_type', 'PRODUCT')[cite: 12]
    product_id = request.form.get('product_id')[cite: 12]
    qty = int(request.form.get('quantity') or 1)[cite: 12]
    dining_opt = request.form.get('dining_option', 'TAKEOUT').upper()[cite: 12]
    notes = request.form.get('notes', '').strip()[cite: 12]
    
    prod_name = 'Custom Receivable Item'[cite: 12]
    unit_p = float(request.form.get('custom_amount') or 0.0)[cite: 12]

    if item_choice_type == 'PRODUCT' and product_id:
        prod = Product.query.get(int(product_id))[cite: 12]
        if prod:
            prod_name = prod.name[cite: 12]
            unit_p = prod.price[cite: 12]
    else:
        prod_name = request.form.get('custom_title', '').strip() or 'Custom Receivable Service'[cite: 12]

    amount = unit_p * qty[cite: 12]

    if amount <= 0:
        flash("Amount must be greater than zero.", "error")[cite: 12]
        return redirect(url_for('cashier_terminal'))[cite: 12]

    cust_id = None[cite: 12]
    cust_name = 'Walk-in Customer'[cite: 12]
    contact = 'N/A'[cite: 12]

    if cust_type == 'REGISTERED':
        reg_id = request.form.get('registered_customer_id')[cite: 12]
        if reg_id:
            cust = Customer.query.get(reg_id)[cite: 12]
            if cust:
                cust_id = cust.id[cite: 12]
                cust_name = cust.name[cite: 12]
                contact = cust.contact[cite: 12]
                cust.outstanding_ar = (cust.outstanding_ar or 0.0) + amount[cite: 12]
    else:
        cust_name = request.form.get('custom_customer_name', '').strip() or 'Custom Account'[cite: 12]
        contact = request.form.get('custom_contact', '').strip() or 'N/A'[cite: 12]

    order = Order(
        order_type='COLLECTION',
        dining_option=dining_opt,
        customer_id=cust_id,
        customer_name=cust_name,
        contact_number=contact,
        subtotal=amount,
        delivery_fee=0.0,
        total_amount=amount,
        payment_method='UNPAID',
        payment_verified=False,
        status='UNPAID_COLLECTION',
        is_unpaid=True,
        collection_notes=notes,
        notes=f"[{dining_opt}] Attributable Item: {prod_name} (x{qty})"
    )[cite: 12]
    db.session.add(order)[cite: 12]
    db.session.flush()[cite: 12]

    db.session.add(OrderItem(
        order_id=order.id,
        product_id=int(product_id) if (item_choice_type == 'PRODUCT' and product_id) else None,
        product_name=prod_name,
        unit_price=unit_p,
        cost_price=0.0,
        quantity=qty,
        subtotal=amount
    ))[cite: 12]

    db.session.commit()[cite: 12]
    flash(f"For Collection ({dining_opt}) recorded for {cust_name}: {prod_name} x{qty} (₱{amount:,.2f})", "info")[cite: 12]
    return redirect(url_for('cashier_terminal'))[cite: 12]

@app.route('/pos/settle-collection/<int:order_id>', methods=['POST'])
@require_cashier
def cashier_settle_collection(order_id):
    order = Order.query.get_or_404(order_id)[cite: 12]
    pay_method = request.form.get('payment_method', 'CASH')[cite: 12]
    
    order.is_unpaid = False[cite: 12]
    order.status = 'COMPLETED'[cite: 12]
    order.payment_method = pay_method[cite: 12]
    order.payment_verified = True[cite: 12]

    is_same_day = (order.created_at.date() == datetime.utcnow().date())[cite: 12]
    earned = 0[cite: 12]

    if order.customer_id:
        cust = Customer.query.get(order.customer_id)[cite: 12]
        if cust:
            cust.outstanding_ar = max(0.0, (cust.outstanding_ar or 0.0) - order.total_amount)[cite: 12]
            cust.accumulated_spend = (cust.accumulated_spend or 0.0) + order.total_amount[cite: 12]
            
            if is_same_day:
                earned = int(order.total_amount // 30)[cite: 12]
                if earned > 0:
                    cust.points_balance = (cust.points_balance or 0.0) + earned[cite: 12]
                    db.session.add(RewardLedger(customer_id=cust.id, points_change=earned, reason=f"Same-Day Settled Credit #{order.id}"))[cite: 12]

    db.session.commit()[cite: 12]
    bonus_msg = f" (+{earned} pts earned for Same-Day payment!)" if earned > 0 else " (No points: paid after order date)"[cite: 12]
    flash(f"Collection #{order.id} for {order.customer_name} settled via {pay_method}!{bonus_msg}", "success")[cite: 12]
    return redirect(url_for('cashier_terminal'))[cite: 12]

@app.route('/pos/settle-customer-credit/<int:cust_id>', methods=['POST'])
@require_cashier
def cashier_settle_customer_credit(cust_id):
    cust = Customer.query.get_or_404(cust_id)[cite: 12]
    amount = float(request.form.get('amount') or cust.outstanding_ar)[cite: 12]
    pay_method = request.form.get('payment_method', 'CASH').upper()[cite: 12]

    if amount <= 0:
        flash("Amount must be greater than zero.", "error")[cite: 12]
        return redirect(url_for('cashier_terminal'))[cite: 12]

    amount_to_pay = min(amount, cust.outstanding_ar)[cite: 12]
    cust.outstanding_ar = max(0.0, cust.outstanding_ar - amount_to_pay)[cite: 12]
    cust.accumulated_spend = (cust.accumulated_spend or 0.0) + amount_to_pay[cite: 12]

    db.session.commit()[cite: 12]
    flash(f"Settled ₱{amount_to_pay:,.2f} credit balance for {cust.name} via {pay_method}!", "success")[cite: 12]
    return redirect(url_for('cashier_terminal'))[cite: 12]

@app.route('/pos/record-expense', methods=['POST'])
@require_cashier
def cashier_record_expense():
    title = request.form.get('title', '').strip()[cite: 12]
    amount = float(request.form.get('amount') or 0.0)[cite: 12]
    category = request.form.get('category', 'Supplies')[cite: 12]
    staff_user = session.get('cashier_user') or session.get('admin_user') or 'Cashier'[cite: 12]

    if not title or amount <= 0:
        flash("Please provide a valid title and amount.", "error")[cite: 12]
        return redirect(url_for('cashier_terminal'))[cite: 12]

    db.session.add(Expense(title=title, amount=amount, category=category, created_by=staff_user))[cite: 12]
    db.session.commit()[cite: 12]
    flash(f"Expense recorded: {title} (₱{amount:,.2f})", "success")[cite: 12]
    return redirect(url_for('cashier_terminal'))[cite: 12]

@app.route('/pos/record-vault-drop', methods=['POST'])
@require_cashier
def cashier_record_vault_drop():
    drop_num = int(request.form.get('drop_number') or 1)[cite: 12]
    amount = float(request.form.get('amount') or 0.0)[cite: 12]
    notes = request.form.get('notes', '').strip()[cite: 12]
    breakdown = request.form.get('cash_breakdown', '').strip()[cite: 12]
    staff_user = session.get('cashier_user') or session.get('admin_user') or 'Cashier'[cite: 12]

    if amount <= 0:
        flash("Drop amount must be greater than zero.", "error")[cite: 12]
        return redirect(url_for('cashier_terminal'))[cite: 12]

    db.session.add(VaultDrop(drop_number=drop_num, amount=amount, notes=notes, cash_breakdown=breakdown, created_by=staff_user))[cite: 12]
    db.session.commit()[cite: 12]
    flash(f"Vault Cash Drop #{drop_num} recorded: ₱{amount:,.2f}", "success")[cite: 12]
    return redirect(url_for('cashier_terminal'))[cite: 12]

@app.route('/pos/update-wifi-minutes/<int:cust_id>', methods=['POST'])
@require_cashier
def cashier_update_wifi_minutes(cust_id):
    cust = Customer.query.get_or_404(cust_id)[cite: 12]
    mins = request.form.get('wifi_minutes')[cite: 12]
    if mins is not None:
        try:
            cust.wifi_minutes_left = max(0, int(mins))[cite: 12]
            db.session.commit()[cite: 12]
            flash(f"Updated Wi-Fi time for {cust.name} to {cust.wifi_minutes_left} mins.", "success")[cite: 12]
        except ValueError:
            flash("Invalid minutes entered.", "error")[cite: 12]
    return redirect(url_for('cashier_terminal'))[cite: 12]

@app.route('/pos/verify/<int:order_id>', methods=['POST'])
@require_cashier
def verify_order(order_id):
    order = Order.query.get_or_404(order_id)[cite: 12]
    action = request.form.get('action')[cite: 12]

    if action == 'ACCEPT':
        order.payment_verified = True[cite: 12]
        order.status = "COMPLETED"[cite: 12]

        if order.customer_id and order.payment_method != "CREDIT":
            cust = Customer.query.get(order.customer_id)[cite: 12]
            if cust:
                cust.accumulated_spend = (cust.accumulated_spend or 0.0) + order.total_amount[cite: 12]
                earned = int(order.total_amount // 30)[cite: 12]
                if earned > 0:
                    cust.points_balance = (cust.points_balance or 0.0) + earned[cite: 12]
                    db.session.add(RewardLedger(customer_id=cust.id, points_change=earned, reason=f"Purchase Order #{order.id}"))[cite: 12]

        db.session.commit()[cite: 12]
        flash(f"Order #{order.id} accepted and completed. Details ready to print!", "success")[cite: 12]
    else:
        for item in order.items:
            if item.product_id:
                prod = Product.query.get(item.product_id)[cite: 12]
                if prod:
                    prod.stock += item.quantity[cite: 12]
        order.status = "CANCELLED"[cite: 12]
        db.session.commit()[cite: 12]
        flash(f"Order #{order.id} cancelled.", "info")[cite: 12]

    return redirect(url_for('cashier_terminal'))[cite: 12]

# ==================== MASTER ADMIN, CONTROLS & SETTINGS ====================

@app.route('/admin')
@require_admin
def admin_dashboard():
    sort_by = request.args.get('sort', 'likes_desc')[cite: 12]

    query = Product.query[cite: 12]
    if sort_by == 'likes_desc': query = query.order_by(Product.total_likes.desc())[cite: 12]
    elif sort_by == 'price_asc': query = query.order_by(Product.price.asc())[cite: 12]
    elif sort_by == 'price_desc': query = query.order_by(Product.price.desc())[cite: 12]
    elif sort_by == 'name_asc': query = query.order_by(Product.name.asc())[cite: 12]
    elif sort_by == 'category': query = query.order_by(Product.category_name.asc(), Product.name.asc())[cite: 12]
    elif sort_by == 'featured': query = query.order_by(Product.is_featured.desc(), Product.name.asc())[cite: 12]
    elif sort_by == 'top_seller': query = query.order_by(Product.is_top_seller.desc(), Product.name.asc())[cite: 12]

    products = query.all()[cite: 12]
    categories = Category.query.all()[cite: 12]
    staff_members = Staff.query.all()[cite: 12]
    customers = Customer.query.order_by(Customer.id.desc()).all()[cite: 12]
    delivery_zones = DeliveryZone.query.all()[cite: 12]
    all_orders = Order.query.order_by(Order.created_at.desc()).limit(150).all()[cite: 12]
    all_expenses = Expense.query.order_by(Expense.created_at.desc()).all()[cite: 12]
    vault_drops = VaultDrop.query.order_by(VaultDrop.created_at.desc()).all()[cite: 12]
    promotions = PromotionTracker.query.order_by(PromotionTracker.created_at.desc()).all()[cite: 12]

    try:
        unique_visitors = SiteVisitor.query.count()[cite: 12]
        total_accumulated_visits = db.session.query(db.func.coalesce(db.func.sum(SiteVisitor.visit_count), 0)).scalar() or unique_visitors[cite: 12]
    except Exception:
        unique_visitors = 1
        total_accumulated_visits = 1

    today = date.today()[cite: 12]
    week_ago = datetime.utcnow() - timedelta(days=7)[cite: 12]
    month_ago = datetime.utcnow() - timedelta(days=30)[cite: 12]

    daily_orders = Order.query.filter(db.func.date(Order.created_at) == today, Order.status == 'COMPLETED').all()[cite: 12]
    weekly_orders = Order.query.filter(Order.created_at >= week_ago, Order.status == 'COMPLETED').all()[cite: 12]
    monthly_orders = Order.query.filter(Order.created_at >= month_ago, Order.status == 'COMPLETED').all()[cite: 12]
    all_completed = Order.query.filter_by(status='COMPLETED').all()[cite: 12]

    daily_exp = db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0.0)).filter(db.func.date(Expense.created_at) == today).scalar() or 0.0[cite: 12]
    weekly_exp = db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0.0)).filter(Expense.created_at >= week_ago).scalar() or 0.0[cite: 12]
    monthly_exp = db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0.0)).filter(Expense.created_at >= month_ago).scalar() or 0.0[cite: 12]
    total_exp_all = sum(e.amount for e in all_expenses)[cite: 12]

    daily_vault = db.session.query(db.func.coalesce(db.func.sum(VaultDrop.amount), 0.0)).filter(db.func.date(VaultDrop.created_at) == today).scalar() or 0.0[cite: 12]
    weekly_vault = db.session.query(db.func.coalesce(db.func.sum(VaultDrop.amount), 0.0)).filter(VaultDrop.created_at >= week_ago).scalar() or 0.0[cite: 12]
    monthly_vault = db.session.query(db.func.coalesce(db.func.sum(VaultDrop.amount), 0.0)).filter(VaultDrop.created_at >= month_ago).scalar() or 0.0[cite: 12]
    all_vault = db.session.query(db.func.coalesce(db.func.sum(VaultDrop.amount), 0.0)).scalar() or 0.0[cite: 12]

    def calc_period(orders, exp, vault_drop_sales):
        order_rev = sum(o.total_amount for o in orders)[cite: 12]
        total_rev = order_rev + vault_drop_sales[cite: 12]
        cost = sum(sum((getattr(it, 'cost_price', 0.0) or 0.0) * it.quantity for it in o.items) for o in orders)[cite: 12]
        gross_p = total_rev - cost[cite: 12]
        net_p = gross_p - exp[cite: 12]
        return {
            'order_rev': order_rev,
            'vault_sales': vault_drop_sales,
            'rev': total_rev,
            'cost': cost,
            'gross_p': gross_p,
            'exp': exp,
            'net_p': net_p
        }[cite: 12]

    fin_daily = calc_period(daily_orders, daily_exp, daily_vault)[cite: 12]
    fin_weekly = calc_period(weekly_orders, weekly_exp, weekly_vault)[cite: 12]
    fin_monthly = calc_period(monthly_orders, monthly_exp, monthly_vault)[cite: 12]
    fin_all = calc_period(all_completed, total_exp_all, all_vault)[cite: 12]

    product_sales_stats = {}[cite: 12]
    food_revenue_total = 0.0[cite: 12]
    service_revenue_total = 0.0[cite: 12]

    for o in all_completed:
        for it in o.items:
            pname = it.product_name[cite: 12]
            if pname not in product_sales_stats:
                product_sales_stats[pname] = {'qty': 0, 'revenue': 0.0, 'cost': 0.0}[cite: 12]
            product_sales_stats[pname]['qty'] += (it.quantity or 0)[cite: 12]
            product_sales_stats[pname]['revenue'] += (it.subtotal or 0.0)[cite: 12]
            product_sales_stats[pname]['cost'] += (getattr(it, 'cost_price', 0.0) or 0.0) * (it.quantity or 0)[cite: 12]

            if '[Service]' in pname or o.order_type == 'SERVICE/MISC' or 'Printing' in pname:
                service_revenue_total += (it.subtotal or 0.0)[cite: 12]
            else:
                food_revenue_total += (it.subtotal or 0.0)[cite: 12]

    food_revenue_total += all_vault[cite: 12]
    total_ar = sum((c.outstanding_ar or 0.0) for c in customers)[cite: 12]

    return render_template('admin.html', 
                           products=products, 
                           categories=categories, 
                           staff_members=staff_members, 
                           customers=customers, 
                           delivery_zones=delivery_zones, 
                           all_orders=all_orders, 
                           all_expenses=all_expenses, 
                           vault_drops=vault_drops, 
                           promotions=promotions, 
                           product_sales_stats=product_sales_stats, 
                           food_revenue_total=food_revenue_total, 
                           service_revenue_total=service_revenue_total, 
                           unique_visitors=unique_visitors, 
                           total_accumulated_visits=total_accumulated_visits, 
                           fin_daily=fin_daily, 
                           fin_weekly=fin_weekly, 
                           fin_monthly=fin_monthly, 
                           fin_all=fin_all, 
                           total_ar=total_ar, 
                           current_sort=sort_by)[cite: 12]

@app.route('/admin/allocate-vault-drop/<int:drop_id>', methods=['POST'])
@require_admin
def admin_allocate_vault_drop(drop_id):
    drop = VaultDrop.query.get_or_404(drop_id)[cite: 12]
    cust_id = request.form.get('customer_id')[cite: 12]
    product_id = request.form.get('product_id')[cite: 12]
    allocated_amount = float(request.form.get('amount') or 0.0)[cite: 12]
    qty = int(request.form.get('quantity') or 1)[cite: 12]

    if allocated_amount <= 0 or allocated_amount > drop.amount:
        flash("Allocated amount must be between ₱0.01 and the remaining drop balance.", "error")[cite: 12]
        return redirect(url_for('admin_dashboard'))[cite: 12]

    cust = Customer.query.get(int(cust_id)) if cust_id else None[cite: 12]
    prod = Product.query.get(int(product_id)) if product_id else None[cite: 12]

    drop.amount = max(0.0, drop.amount - allocated_amount)[cite: 12]

    order = Order(
        order_type='ALLOCATED_VAULT_SALE',
        dining_option='DINE-IN',
        customer_id=cust.id if cust else None,
        customer_name=cust.name if cust else 'Allocated Vault Customer',
        contact_number=cust.contact if cust else 'N/A',
        subtotal=allocated_amount,
        delivery_fee=0.0,
        total_amount=allocated_amount,
        payment_method='CASH',
        payment_verified=True,
        status='COMPLETED',
        notes=f"Allocated from Vault Drop #{drop.drop_number}"
    )[cite: 12]
    db.session.add(order)[cite: 12]
    db.session.flush()[cite: 12]

    db.session.add(OrderItem(
        order_id=order.id,
        product_id=prod.id if prod else None,
        product_name=prod.name if prod else f"Ulam Sale (Drop #{drop.drop_number})",
        unit_price=allocated_amount / qty,
        cost_price=0.0,
        quantity=qty,
        subtotal=allocated_amount
    ))[cite: 12]

    if cust:
        cust.accumulated_spend = (cust.accumulated_spend or 0.0) + allocated_amount[cite: 12]
        earned = int(allocated_amount // 30)[cite: 12]
        if earned > 0:
            cust.points_balance = (cust.points_balance or 0.0) + earned[cite: 12]
            db.session.add(RewardLedger(
                customer_id=cust.id,
                points_change=earned,
                reason=f"Allocated Sale from Drop #{drop.drop_number}"
            ))[cite: 12]

    db.session.commit()[cite: 12]
    flash(f"Allocated ₱{allocated_amount:,.2f} from Drop #{drop.drop_number} into a dedicated Order #{order.id}!", "success")[cite: 12]
    return redirect(url_for('admin_dashboard'))[cite: 12]

@app.route('/admin/reassign-order/<int:order_id>', methods=['POST'])
@require_admin
def admin_reassign_order(order_id):
    order = Order.query.get_or_404(order_id)[cite: 12]
    new_cust_id = request.form.get('customer_id')[cite: 12]

    if not new_cust_id:
        flash("Please select a target customer.", "error")[cite: 12]
        return redirect(url_for('admin_dashboard'))[cite: 12]

    new_cust = Customer.query.get_or_404(int(new_cust_id))[cite: 12]
    old_cust = Customer.query.get(order.customer_id) if order.customer_id else None[cite: 12]

    if old_cust and order.status == 'COMPLETED':
        earned = int(order.total_amount // 30)[cite: 12]
        old_cust.points_balance = max(0.0, (old_cust.points_balance or 0.0) - earned)[cite: 12]
        old_cust.accumulated_spend = max(0.0, (old_cust.accumulated_spend or 0.0) - order.total_amount)[cite: 12]

    order.customer_id = new_cust.id[cite: 12]
    order.customer_name = new_cust.name[cite: 12]
    order.contact_number = new_cust.contact[cite: 12]

    if order.status == 'COMPLETED':
        earned_new = int(order.total_amount // 30)[cite: 12]
        new_cust.accumulated_spend = (new_cust.accumulated_spend or 0.0) + order.total_amount[cite: 12]
        if earned_new > 0:
            new_cust.points_balance = (new_cust.points_balance or 0.0) + earned_new[cite: 12]
            db.session.add(RewardLedger(
                customer_id=new_cust.id,
                points_change=earned_new,
                reason=f"Admin Reassigned Order #{order.id}"
            ))[cite: 12]

    db.session.commit()[cite: 12]
    flash(f"Transaction #{order.id} reassigned to '{new_cust.name}'.", "success")[cite: 12]
    return redirect(url_for('admin_dashboard'))[cite: 12]

@app.route('/admin/update-expense/<int:expense_id>', methods=['POST'])
@require_admin
def admin_update_expense(expense_id):
    exp = Expense.query.get_or_404(expense_id)[cite: 12]
    exp.title = request.form.get('title', exp.title).strip()[cite: 12]
    exp.amount = float(request.form.get('amount') or exp.amount)[cite: 12]
    exp.category = request.form.get('category', exp.category).strip()[cite: 12]
    db.session.commit()[cite: 12]
    flash(f"Expense #{exp.id} updated successfully.", "success")[cite: 12]
    return redirect(url_for('admin_dashboard'))[cite: 12]

@app.route('/admin/delete-expense/<int:expense_id>', methods=['POST'])
@require_admin
def admin_delete_expense(expense_id):
    exp = Expense.query.get_or_404(expense_id)[cite: 12]
    db.session.delete(exp)[cite: 12]
    db.session.commit()[cite: 12]
    flash(f"Expense record removed.", "info")[cite: 12]
    return redirect(url_for('admin_dashboard'))[cite: 12]

@app.route('/admin/delete-product/<int:product_id>', methods=['POST'])
@require_admin
def admin_delete_product(product_id):
    prod = Product.query.get_or_404(product_id)[cite: 12]
    prod_name = prod.name[cite: 12]

    OrderItem.query.filter_by(product_id=prod.id).update({'product_id': None})[cite: 12]
    ProductLike.query.filter_by(product_id=prod.id).delete()[cite: 12]
    ProductComment.query.filter_by(product_id=prod.id).delete()[cite: 12]

    db.session.delete(prod)[cite: 12]
    db.session.commit()[cite: 12]
    flash(f"Product '{prod_name}' permanently deleted.", "info")[cite: 12]
    return redirect(url_for('admin_dashboard'))[cite: 12]

@app.route('/admin/revert-order/<int:order_id>', methods=['POST'])
@require_admin
def admin_revert_order(order_id):
    order = Order.query.get_or_404(order_id)[cite: 12]
    
    for item in order.items:
        if item.product_id:
            p = Product.query.get(item.product_id)[cite: 12]
            if p:
                p.stock += item.quantity[cite: 12]

    if order.customer_id and order.status == 'COMPLETED':
        cust = Customer.query.get(order.customer_id)[cite: 12]
        if cust:
            earned = int(order.total_amount // 30)[cite: 12]
            cust.points_balance = max(0.0, (cust.points_balance or 0.0) - earned)[cite: 12]
            cust.accumulated_spend = max(0.0, (cust.accumulated_spend or 0.0) - order.total_amount)[cite: 12]
            db.session.add(RewardLedger(
                customer_id=cust.id,
                points_change=-earned,
                reason=f"Admin Reverted Sale #{order.id}"
            ))[cite: 12]

    if order.is_unpaid and order.customer_id:
        cust = Customer.query.get(order.customer_id)[cite: 12]
        if cust:
            cust.outstanding_ar = max(0.0, (cust.outstanding_ar or 0.0) - order.total_amount)[cite: 12]

    db.session.delete(order)[cite: 12]
    db.session.commit()[cite: 12]
    flash(f"Order #{order_id} deleted & reverted.", "info")
    return redirect(url_for('admin_dashboard'))[cite: 12]

@app.route('/admin/purge-dummy-orders/<int:cust_id>', methods=['POST'])
@require_admin
def admin_purge_dummy_orders(cust_id):
    cust = Customer.query.get_or_404(cust_id)[cite: 12]
    dummy_orders = Order.query.filter_by(customer_id=cust.id).all()[cite: 12]
    for o in dummy_orders:
        db.session.delete(o)[cite: 12]
    cust.points_balance = 0.0[cite: 12]
    cust.accumulated_spend = 0.0[cite: 12]
    cust.outstanding_ar = 0.0[cite: 12]
    RewardLedger.query.filter_by(customer_id=cust.id).delete()[cite: 12]
    db.session.commit()[cite: 12]
    flash(f"Purged test orders & reset points for '{cust.name}'.", "info")
    return redirect(url_for('admin_dashboard'))[cite: 12]

@app.route('/admin/delete-customer/<int:cust_id>', methods=['POST'])
@require_admin
def admin_delete_customer(cust_id):
    cust = Customer.query.get_or_404(cust_id)[cite: 12]
    Order.query.filter_by(customer_id=cust.id).delete()[cite: 12]
    RewardLedger.query.filter_by(customer_id=cust.id).delete()[cite: 12]
    ProductLike.query.filter_by(customer_id=cust.id).delete()[cite: 12]
    ProductComment.query.filter_by(customer_id=cust.id).delete()[cite: 12]
    db.session.delete(cust)[cite: 12]
    db.session.commit()[cite: 12]
    flash(f"Account '{cust.name}' permanently removed.", "success")[cite: 12]
    return redirect(url_for('admin_dashboard'))[cite: 12]

@app.route('/admin/update-logo', methods=['POST'])
@require_admin
def admin_update_logo():
    new_logo = request.form.get('logo_url', '').strip()[cite: 12]
    if new_logo:
        setting = StoreSetting.query.filter_by(key='logo_url').first()[cite: 12]
        if not setting:
            db.session.add(StoreSetting(key='logo_url', value=new_logo))[cite: 12]
        else:
            setting.value = new_logo[cite: 12]
        db.session.commit()[cite: 12]
        flash("Company logo updated across all portals.", "success")[cite: 12]
    return redirect(url_for('admin_dashboard'))[cite: 12]

@app.route('/admin/add-product', methods=['POST'])
@require_admin
def admin_add_product():
    name = request.form.get('name', '').strip()[cite: 12]
    category_name = request.form.get('category_name', 'Meals')[cite: 12]
    price = float(request.form.get('price') or 0.0)[cite: 12]
    stock = int(request.form.get('stock') or 100)[cite: 12]
    image_url = request.form.get('image_url', '').strip()[cite: 12]
    start_t = request.form.get('available_start_time', '').strip() or None[cite: 12]
    end_t = request.form.get('available_end_time', '').strip() or None[cite: 12]
    is_featured = bool(request.form.get('is_featured'))[cite: 12]
    is_top_seller = bool(request.form.get('is_top_seller'))[cite: 12]

    if not name or price <= 0:
        flash("Please enter a valid product name and price.", "error")
        return redirect(url_for('admin_dashboard'))[cite: 12]

    db.session.add(Product(name=name, category_name=category_name, price=price, cost=0.0, stock=stock, 
                           image_url=image_url, available_start_time=start_t, available_end_time=end_t,
                           is_featured=is_featured, is_top_seller=is_top_seller, is_active=True))[cite: 12]
    db.session.commit()[cite: 12]
    flash(f"Product '{name}' added successfully!", "success")
    return redirect(url_for('admin_dashboard'))[cite: 12]

@app.route('/admin/batch-update-products', methods=['POST'])
@require_admin
def admin_batch_update_products():
    for pid in request.form.getlist('product_id'):[cite: 12]
        prod = Product.query.get(pid)[cite: 12]
        if prod:
            prod.price = float(request.form.get(f'price_{pid}') or prod.price)[cite: 12]
            prod.stock = int(request.form.get(f'stock_{pid}') or prod.stock)[cite: 12]
            prod.image_url = request.form.get(f'image_url_{pid}', '').strip()[cite: 12]
            prod.available_start_time = request.form.get(f'available_start_time_{pid}', '').strip() or None[cite: 12]
            prod.available_end_time = request.form.get(f'available_end_time_{pid}', '').strip() or None[cite: 12]
            prod.is_active = (f'is_active_{pid}' in request.form)[cite: 12]
            prod.is_featured = (f'is_featured_{pid}' in request.form)[cite: 12]
            prod.is_top_seller = (f'is_top_seller_{pid}' in request.form)[cite: 12]
    db.session.commit()[cite: 12]
    flash("Bulk product catalog updated.", "success")[cite: 12]
    return redirect(url_for('admin_dashboard'))[cite: 12]

@app.route('/admin/toggle-credit/<int:cust_id>', methods=['POST'])
@require_admin
def admin_toggle_credit(cust_id):
    cust = Customer.query.get_or_404(cust_id)[cite: 12]
    cust.is_credit_eligible = not cust.is_credit_eligible[cite: 12]
    limit = request.form.get('credit_limit')[cite: 12]
    if limit:
        cust.credit_limit = float(limit)[cite: 12]
    db.session.commit()[cite: 12]
    flash(f"Credit eligibility updated for {cust.name}.", "success")[cite: 12]
    return redirect(url_for('admin_dashboard'))[cite: 12]

@app.route('/admin/delivery-zones', methods=['POST'])
@require_admin
def admin_manage_delivery_zones():
    action = request.form.get('action')[cite: 12]
    if action == 'ADD':
        place = request.form.get('place_name')[cite: 12]
        brgy = request.form.get('barangay')[cite: 12]
        rate = float(request.form.get('rate') or 40.0)[cite: 12]
        dist = request.form.get('distance')[cite: 12]
        note = request.form.get('note')[cite: 12]
        db.session.add(DeliveryZone(place_name=place, barangay=brgy, rate=rate, distance=dist, note=note))[cite: 12]
    elif action == 'DELETE':
        zid = request.form.get('zone_id')[cite: 12]
        zone = DeliveryZone.query.get(zid)[cite: 12]
        if zone:
            db.session.delete(zone)[cite: 12]
    db.session.commit()[cite: 12]
    flash("Delivery zones updated.", "success")[cite: 12]
    return redirect(url_for('admin_dashboard'))[cite: 12]

@app.route('/admin/reset-customer-pin/<int:cust_id>', methods=['POST'])
@require_admin
def admin_reset_customer_pin(cust_id):
    cust = Customer.query.get_or_404(cust_id)[cite: 12]
    new_pin = request.form.get('new_pin', '').strip()[cite: 12]
    if not new_pin or len(new_pin) < 4:
        flash("PIN must be at least 4 digits.", "error")[cite: 12]
    else:
        cust.pin_hash = generate_password_hash(new_pin)[cite: 12]
        db.session.commit()[cite: 12]
        flash(f"PIN for customer '{cust.name}' reset to {new_pin}.", "success")[cite: 12]
    return redirect(url_for('admin_dashboard'))[cite: 12]

@app.route('/admin/toggle-promo/<int:promo_id>', methods=['POST'])
@require_admin
def admin_toggle_promo(promo_id):
    promo = PromotionTracker.query.get_or_404(promo_id)[cite: 12]
    promo.is_active = not promo.is_active[cite: 12]
    if promo.is_active:
        promo.created_at = datetime.utcnow()[cite: 12]
    db.session.commit()[cite: 12]
    flash(f"Campaign '{promo.title}' status updated.", "success")
    return redirect(url_for('admin_dashboard'))[cite: 12]

@app.route('/admin/toggle-promo-visibility/<int:promo_id>', methods=['POST'])
@require_admin
def admin_toggle_promo_visibility(promo_id):
    promo = PromotionTracker.query.get_or_404(promo_id)[cite: 12]
    promo.is_visible = not getattr(promo, 'is_visible', True)[cite: 12]
    db.session.commit()[cite: 12]
    flash(f"Promo '{promo.title}' visibility updated.", "info")
    return redirect(url_for('admin_dashboard'))[cite: 12]

# ==================== CUSTOMER PORTAL ====================

@app.route('/portal/login', methods=['GET', 'POST'])
def customer_login():
    if request.method == 'POST':
        contact = request.form.get('contact', '').strip()[cite: 12]
        pin = request.form.get('pin', '').strip()[cite: 12]
        cust = Customer.query.filter_by(contact=contact).first()[cite: 12]
        if cust and check_password_hash(cust.pin_hash, pin):
            session['customer_id'] = cust.id[cite: 12]
            today = date.today()[cite: 12]

            if cust.last_daily_login != today:
                yesterday = today - timedelta(days=1)[cite: 12]
                if cust.last_daily_login == yesterday:
                    cust.login_streak = (cust.login_streak or 0) + 1[cite: 12]
                else:
                    cust.login_streak = 1[cite: 12]
                
                cust.points_balance = (cust.points_balance or 0.0) + 0.5[cite: 12]
                cust.last_daily_login = today[cite: 12]
                db.session.add(RewardLedger(
                    customer_id=cust.id,
                    points_change=0.5,
                    reason=f"Daily Login Reward (Day {cust.login_streak})"
                ))[cite: 12]

            cust.last_active_at = datetime.utcnow()[cite: 12]
            db.session.commit()[cite: 12]
            return redirect(url_for('customer_dashboard'))[cite: 12]
        flash("Invalid Contact or PIN.", "error")[cite: 12]
    return render_template('customer_login.html')[cite: 12]

@app.route('/portal/register', methods=['GET', 'POST'])
def customer_register():
    ref_code = request.args.get('ref', '').strip()[cite: 12]
    if request.method == 'POST':
        name = request.form.get('name', '').strip()[cite: 12]
        email = request.form.get('email', '').strip()[cite: 12]
        contact = request.form.get('contact', '').strip()[cite: 12]
        messenger = request.form.get('fb_messenger', '').strip()[cite: 12]
        pin = request.form.get('pin', '').strip()[cite: 12]
        address = request.form.get('default_address', '').strip()[cite: 12]
        landmark = request.form.get('default_landmark', '').strip()[cite: 12]
        ref = request.form.get('referral_code', '').strip() or ref_code[cite: 12]

        if Customer.query.filter_by(contact=contact).first():
            flash("Contact number already registered.", "error")[cite: 12]
            return redirect(url_for('customer_register'))[cite: 12]

        new_cust = Customer(
            name=name,
            email=email,
            contact=contact,
            fb_messenger=messenger,
            default_address=address,
            default_landmark=landmark,
            points_balance=0.5,
            pin_hash=generate_password_hash(pin),
            card_number=f"MFH-{random.randint(1, 100):04d}",
            card_expires_at=date.today() + timedelta(days=365),
            referred_by=ref if ref else None,
            last_daily_login=date.today(),
            login_streak=1,
            wifi_minutes_left=10,
            wifi_voucher_code="MFH-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6)),
            last_active_at=datetime.utcnow()
        )[cite: 12]
        db.session.add(new_cust)[cite: 12]
        db.session.flush()[cite: 12]

        db.session.add(RewardLedger(
            customer_id=new_cust.id,
            points_change=0.5,
            reason="Welcome Login Bonus"
        ))[cite: 12]

        if ref:
            referrer = Customer.query.filter((Customer.card_number == ref) | (Customer.contact == ref)).first()[cite: 12]
            if referrer:
                referrer.points_balance = (referrer.points_balance or 0.0) + 2.0[cite: 12]
                db.session.add(RewardLedger(
                    customer_id=referrer.id,
                    points_change=2.0,
                    reason=f"Referral Bonus: Invited {name}"
                ))[cite: 12]

        db.session.commit()[cite: 12]
        session['customer_id'] = new_cust.id[cite: 12]
        flash("🎉 Welcome! You earned 0.5 points and 10 mins free Wi-Fi!", "success")[cite: 12]
        return redirect(url_for('customer_dashboard'))[cite: 12]
    return render_template('customer_register.html', ref_code=ref_code)[cite: 12]

@app.route('/portal/dashboard')
def customer_dashboard():
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))[cite: 12]
    
    cust = Customer.query.get(session['customer_id'])[cite: 12]
    if not cust:
        session.pop('customer_id', None)[cite: 12]
        flash("Account session expired. Please log in again.", "info")[cite: 12]
        return redirect(url_for('customer_login'))[cite: 12]
    
    if getattr(cust, 'login_streak', None) is None:
        cust.login_streak = 1[cite: 12]
        db.session.commit()[cite: 12]

    my_orders = Order.query.filter_by(customer_id=cust.id).order_by(Order.created_at.desc()).all()[cite: 12]
    promo_burger = PromotionTracker.query.filter_by(promo_code='BURGER_FRIES_50', is_visible=True).first()[cite: 12]
    promo_nachos = PromotionTracker.query.filter_by(promo_code='BEEFY_NACHOS_75', is_visible=True).first()[cite: 12]
    
    return render_template('customer_dashboard.html', 
                           cust=cust, 
                           orders=my_orders, 
                           promo_burger=promo_burger, 
                           promo_nachos=promo_nachos, 
                           today=date.today())[cite: 12]

@app.route('/portal/logout')
def customer_logout():
    if 'customer_id' in session:
        try:
            cust = Customer.query.get(session['customer_id'])[cite: 12]
            if cust and hasattr(cust, 'last_active_at'):
                cust.last_active_at = datetime.utcnow() - timedelta(hours=1)[cite: 12]
                db.session.commit()[cite: 12]
        except Exception:
            db.session.rollback()[cite: 12]
    session.pop('customer_id', None)[cite: 12]
    flash("Successfully logged out.", "info")[cite: 12]
    return redirect(url_for('store_catalog'))[cite: 12]

@app.route('/portal/reserve-promo/<string:promo_code>', methods=['POST'])
def customer_reserve_promo_by_code(promo_code):
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))[cite: 12]
    
    cust = Customer.query.get_or_404(session['customer_id'])[cite: 12]
    promo = PromotionTracker.query.filter_by(promo_code=promo_code).first()[cite: 12]

    if not promo or not promo.is_active:
        flash("This promotion campaign is currently archived.", "info")[cite: 12]
        return redirect(url_for('customer_dashboard'))[cite: 12]

    days_active = (datetime.utcnow() - promo.created_at).days[cite: 12]
    if days_active > 3:
        promo.is_active = False[cite: 12]
        db.session.commit()[cite: 12]
        flash("This 3-day promotion campaign has ended and is now archived.", "info")[cite: 12]
        return redirect(url_for('customer_dashboard'))[cite: 12]

    order = Order(
        order_type='PICKUP',
        dining_option='TAKEOUT',
        customer_id=cust.id,
        customer_name=f"{cust.name} (Member Promo)",
        contact_number=cust.contact,
        pickup_time='Today / In-Store Claim',
        target_time='In-Store Counter Claim',
        subtotal=promo.promo_price,
        delivery_fee=0.0,
        total_amount=promo.promo_price,
        payment_method='CASH',
        payment_verified=False,
        status='VERIFICATION',
        notes=f"[3-DAY PROMO CLAIM] {promo.title} (₱{promo.promo_price:,.2f} Deal)"
    )[cite: 12]
    db.session.add(order)[cite: 12]
    db.session.flush()[cite: 12]

    db.session.add(OrderItem(
        order_id=order.id,
        product_id=None,
        product_name=f"[PROMO 3-DAY] {promo.title}",
        unit_price=promo.promo_price,
        cost_price=0.0,
        quantity=1,
        subtotal=promo.promo_price
    ))[cite: 12]

    promo.claims_count = (promo.claims_count or 0) + 1[cite: 12]
    promo.total_revenue = (promo.total_revenue or 0.0) + promo.promo_price[cite: 12]

    db.session.commit()[cite: 12]
    flash(f"🎉 Deal reserved! Order #{order.id} queued at Cashier counter.", "success")[cite: 12]
    return redirect(url_for('customer_dashboard'))[cite: 12]

@app.route('/portal/update-profile-pic', methods=['POST'])
def update_profile_pic():
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))[cite: 12]
    cust = Customer.query.get(session['customer_id'])[cite: 12]
    img_url = request.form.get('profile_image', '').strip()[cite: 12]
    if img_url:
        cust.profile_image = img_url[cite: 12]
        db.session.commit()[cite: 12]
        flash("Profile picture updated!", "success")[cite: 12]
    return redirect(url_for('customer_dashboard'))[cite: 12]

# ==================== INDEPENDENT STAFF AUTH ====================

@app.route('/staff/login', methods=['GET', 'POST'])
def staff_login():
    target = request.args.get('target', '').lower()[cite: 12]
    if request.method == 'POST':
        user = request.form.get('username', '').strip().lower()[cite: 12]
        pin = request.form.get('pin', '').strip()[cite: 12]
        staff = Staff.query.filter(db.func.lower(Staff.username) == user).first()[cite: 12]

        if staff and check_password_hash(staff.pin_hash, pin):
            if staff.role == 'ADMIN':
                session['admin_id'] = staff.id[cite: 12]
                session['admin_user'] = staff.username[cite: 12]
                return redirect(url_for('admin_dashboard'))[cite: 12]
            elif staff.role == 'CASHIER':
                session['cashier_id'] = staff.id[cite: 12]
                session['cashier_user'] = staff.username[cite: 12]
                return redirect(url_for('cashier_terminal'))[cite: 12]
        flash('Invalid Username or PIN.', 'error')[cite: 12]
    return render_template('staff_login.html', target=target)[cite: 12]

@app.route('/staff/logout')
def staff_logout():
    role = request.args.get('role')[cite: 12]
    if role == 'admin': session.pop('admin_id', None); session.pop('admin_user', None)[cite: 12]
    elif role == 'cashier': session.pop('cashier_id', None); session.pop('cashier_user', None)[cite: 12]
    else: session.clear()[cite: 12]
    flash('Logged out.', 'info')[cite: 12]
    return redirect(url_for('staff_login'))[cite: 12]

if __name__ == '__main__':
    run_db_setup()
    app.run(debug=True, port=5000)