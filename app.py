import io
import json
import logging
import os
import re
import secrets
from datetime import datetime, date, timedelta, time, timezone
from functools import wraps
from zoneinfo import ZoneInfo

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_from_directory, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text, UniqueConstraint
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix

import qrcode
import qrcode.image.svg

logging.basicConfig(
    level=os.environ.get('LOG_LEVEL', 'INFO').upper(),
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)

app = Flask(__name__)
# Trust Render's single reverse-proxy hop so generated QR URLs use the public HTTPS host.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
IS_PRODUCTION = bool(os.environ.get('RENDER') or os.environ.get('FLASK_ENV') == 'production')
_secret_key = os.environ.get('SECRET_KEY')
if not _secret_key:
    _secret_key = secrets.token_hex(32)
    app.logger.warning('SECRET_KEY is not configured; generated a temporary key. Set SECRET_KEY in Render for stable sessions.')
app.config['SECRET_KEY'] = _secret_key

database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///foodhouse_pos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = IS_PRODUCTION

db = SQLAlchemy(app)

MANILA_TZ = ZoneInfo('Asia/Manila')
STAFF_SESSION_TIMEOUT = timedelta(hours=8)
_DB_INITIALIZED = False

def utc_now():
    """UTC-naive timestamp for backwards-compatible database storage."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

def ph_now():
    return datetime.now(MANILA_TZ)

def ph_today():
    return ph_now().date()

def ph_day_utc_bounds(day=None):
    """Return UTC-naive [start, end) bounds for one Philippine calendar day."""
    day = day or ph_today()
    start_local = datetime.combine(day, time.min, tzinfo=MANILA_TZ)
    next_local = start_local + timedelta(days=1)
    return (
        start_local.astimezone(timezone.utc).replace(tzinfo=None),
        next_local.astimezone(timezone.utc).replace(tzinfo=None),
    )

def utc_naive_to_ph(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(MANILA_TZ)

# ==================== DATA MODELS ====================

class StoreSetting(db.Model):
    __tablename__ = 'store_setting'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)

class Staff(db.Model):
    __tablename__ = 'staff'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    pin_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    active = db.Column(db.Boolean, default=True)

class Customer(db.Model):
    __tablename__ = 'customer'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    contact = db.Column(db.String(30), unique=True, nullable=False)
    fb_messenger = db.Column(db.String(150), nullable=True)
    pin_hash = db.Column(db.String(255), nullable=False)
    profile_image = db.Column(db.Text, nullable=True)
    default_address = db.Column(db.Text, nullable=True)
    default_landmark = db.Column(db.String(150), nullable=True)
    points_balance = db.Column(db.Float, default=0.0)
    is_credit_eligible = db.Column(db.Boolean, default=False)
    credit_limit = db.Column(db.Float, default=0.0)
    outstanding_ar = db.Column(db.Float, default=0.0)
    accumulated_spend = db.Column(db.Float, default=0.0)
    card_number = db.Column(db.String(20), unique=True, nullable=True)
    card_status = db.Column(db.String(20), default="ACTIVE")
    card_expires_at = db.Column(db.Date, nullable=True)
    referred_by = db.Column(db.String(50), nullable=True)
    last_daily_login = db.Column(db.Date, nullable=True)
    login_streak = db.Column(db.Integer, default=1)
    wifi_voucher_code = db.Column(db.String(20), nullable=True)
    wifi_minutes_left = db.Column(db.Integer, default=0)
    last_active_at = db.Column(db.DateTime, default=utc_now)
    created_at = db.Column(db.DateTime, default=utc_now)

class DeliveryZone(db.Model):
    __tablename__ = 'delivery_zone'
    id = db.Column(db.Integer, primary_key=True)
    place_name = db.Column(db.String(100), nullable=False)
    barangay = db.Column(db.String(100), nullable=False)
    rate = db.Column(db.Float, nullable=False)
    distance = db.Column(db.String(50), nullable=True)
    note = db.Column(db.String(150), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category_name = db.Column(db.String(80), nullable=False)
    price = db.Column(db.Float, nullable=False)
    cost = db.Column(db.Float, default=0.0, nullable=True)
    allow_custom_amount = db.Column(db.Boolean, default=False)
    minimum_order_amount = db.Column(db.Float, nullable=True)
    option_schema = db.Column(db.Text, nullable=True)
    stock = db.Column(db.Integer, default=100)
    image_url = db.Column(db.Text, nullable=True)
    is_featured = db.Column(db.Boolean, default=False)
    is_top_seller = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    available_start_time = db.Column(db.String(10), nullable=True)
    available_end_time = db.Column(db.String(10), nullable=True)
    total_likes = db.Column(db.Integer, default=0)
    comments = db.relationship('ProductComment', backref='product_rel', cascade="all, delete-orphan", lazy=True)

class ProductLike(db.Model):
    __tablename__ = 'product_like'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id', ondelete='CASCADE'), nullable=False)
    ip_address = db.Column(db.String(50), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

class ProductComment(db.Model):
    __tablename__ = 'product_comment'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id', ondelete='CASCADE'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id', ondelete='SET NULL'), nullable=True)
    author_name = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(50), nullable=False)
    comment_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

class Order(db.Model):
    __tablename__ = 'order'
    id = db.Column(db.Integer, primary_key=True)
    order_type = db.Column(db.String(30), nullable=False)
    dining_option = db.Column(db.String(20), default='DINE-IN')
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    customer_name = db.Column(db.String(100), default='Customer')
    contact_number = db.Column(db.String(50), default='N/A')
    fb_messenger = db.Column(db.String(150), nullable=True)
    delivery_address = db.Column(db.Text, nullable=True)
    landmark = db.Column(db.String(150), nullable=True)
    pickup_time = db.Column(db.String(50), nullable=True)
    target_time = db.Column(db.String(50), nullable=True)
    change_for = db.Column(db.Float, nullable=True)
    gcash_ref = db.Column(db.String(10), nullable=True)
    subtotal = db.Column(db.Float, nullable=False)
    delivery_fee = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)
    payment_verified = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(30), default="VERIFICATION")
    is_unpaid = db.Column(db.Boolean, default=False)
    collection_notes = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=False, default="None")
    created_at = db.Column(db.DateTime, default=utc_now)
    customer = db.relationship('Customer', backref='orders', lazy=True)
    items = db.relationship('OrderItem', backref='order_rel', cascade="all, delete-orphan", lazy=True)

class OrderItem(db.Model):
    __tablename__ = 'order_item'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    product_name = db.Column(db.String(120), nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    cost_price = db.Column(db.Float, default=0.0, nullable=True)
    quantity = db.Column(db.Integer, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    selected_options = db.Column(db.Text, nullable=True)

class Expense(db.Model):
    __tablename__ = 'expense'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), default='General')
    created_by = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

class VaultDrop(db.Model):
    __tablename__ = 'vault_drop'
    id = db.Column(db.Integer, primary_key=True)
    drop_number = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    notes = db.Column(db.String(255), nullable=True)
    cash_breakdown = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

class ChangeFund(db.Model):
    __tablename__ = 'change_fund'
    id = db.Column(db.Integer, primary_key=True)
    fund_title = db.Column(db.String(150), nullable=False, default="Cashier Opening Change Fund")
    amount = db.Column(db.Float, nullable=False)
    notes = db.Column(db.String(255), nullable=True)
    created_by = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

class RewardLedger(db.Model):
    __tablename__ = 'reward_ledger'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    points_change = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(150), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

class SiteVisitor(db.Model):
    __tablename__ = 'site_visitor'
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(50), unique=True, nullable=False)
    visit_count = db.Column(db.Integer, default=1)
    visited_at = db.Column(db.DateTime, default=utc_now)

class PromotionTracker(db.Model):
    __tablename__ = 'promotion_tracker'
    id = db.Column(db.Integer, primary_key=True)
    promo_code = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    promo_price = db.Column(db.Float, nullable=False)
    promo_cost = db.Column(db.Float, default=0.0, nullable=True)
    page_views = db.Column(db.Integer, default=0)
    claims_count = db.Column(db.Integer, default=0)
    total_revenue = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    is_visible = db.Column(db.Boolean, default=True)
    portal_only = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utc_now)

# Legacy historical tables retained for non-destructive compatibility with older deployments.
class CustomerWishlist(db.Model):
    __tablename__ = 'customer_wishlist'
    __table_args__ = (UniqueConstraint('customer_id', 'product_id', name='uq_customer_wishlist_product'),)
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

class MenuVote(db.Model):
    __tablename__ = 'menu_vote'
    __table_args__ = (UniqueConstraint('customer_id', 'product_id', 'period_key', name='uq_menu_vote_period'),)
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id', ondelete='CASCADE'), nullable=False)
    period_key = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

class EngagementClaim(db.Model):
    __tablename__ = 'engagement_claim'
    __table_args__ = (UniqueConstraint('customer_id', 'action_code', 'period_key', name='uq_engagement_claim_period'),)
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id', ondelete='CASCADE'), nullable=False)
    action_code = db.Column(db.String(50), nullable=False)
    period_key = db.Column(db.String(30), nullable=False)
    points_awarded = db.Column(db.Float, default=0.0, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

class BonusCampaign(db.Model):
    __tablename__ = 'bonus_campaign'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    bonus_points = db.Column(db.Float, nullable=False, default=0.0)
    points_multiplier = db.Column(db.Float, nullable=False, default=1.0)
    min_spend = db.Column(db.Float, nullable=False, default=0.0)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    start_time = db.Column(db.String(5), nullable=True)
    end_time = db.Column(db.String(5), nullable=True)
    weekdays = db.Column(db.String(30), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)

class BonusCampaignClaim(db.Model):
    __tablename__ = 'bonus_campaign_claim'
    __table_args__ = (UniqueConstraint('campaign_id', 'order_id', name='uq_bonus_campaign_order'),)
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('bonus_campaign.id', ondelete='CASCADE'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id', ondelete='CASCADE'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id', ondelete='CASCADE'), nullable=False)
    points_awarded = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

class ReferralReward(db.Model):
    __tablename__ = 'referral_reward'
    __table_args__ = (UniqueConstraint('referred_customer_id', name='uq_referral_referred_customer'),)
    id = db.Column(db.Integer, primary_key=True)
    referrer_customer_id = db.Column(db.Integer, db.ForeignKey('customer.id', ondelete='CASCADE'), nullable=False)
    referred_customer_id = db.Column(db.Integer, db.ForeignKey('customer.id', ondelete='CASCADE'), nullable=False)
    first_order_id = db.Column(db.Integer, db.ForeignKey('order.id', ondelete='SET NULL'), nullable=True)
    referrer_points = db.Column(db.Float, default=0.0, nullable=False)
    referred_points = db.Column(db.Float, default=0.0, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

class PortalEvent(db.Model):
    __tablename__ = 'portal_event'
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(30), nullable=True)
    event_type = db.Column(db.String(50), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

class ProductSuggestion(db.Model):
    __tablename__ = 'product_suggestion'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id', ondelete='SET NULL'), nullable=True)
    customer_name = db.Column(db.String(100), nullable=False)
    suggestion_text = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='NEW')
    created_at = db.Column(db.DateTime, default=utc_now)

SUGGESTION_STATUSES = ('NEW', 'CONSIDERING', 'PLANNED', 'AVAILABLE', 'ARCHIVED')

# ==================== PWA ROOT ROUTES ====================

@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'manifest.json', mimetype='application/manifest+json')

@app.route('/sw.js')
def serve_sw():
    response = send_from_directory(os.path.join(app.root_path, 'static'), 'sw.js', mimetype='application/javascript')
    response.headers['Service-Worker-Allowed'] = '/'
    return response

# ==================== SAFE MIGRATION & RUN HOOKS ====================

def _ensure_column(table_name, column_name, ddl_type):
    """Idempotently add one missing column on SQLite or PostgreSQL."""
    inspector = inspect(db.engine)
    existing = {c['name'] for c in inspector.get_columns(table_name)}
    if column_name in existing:
        return False

    prep = db.engine.dialect.identifier_preparer
    q_table = prep.quote(table_name)
    q_col = prep.quote(column_name)
    try:
        with db.engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {q_table} ADD COLUMN {q_col} {ddl_type}"))
        app.logger.info('Database migration: added %s.%s', table_name, column_name)
        return True
    except Exception:
        # Another process may have applied it after our inspection. Re-check before failing.
        inspector = inspect(db.engine)
        existing = {c['name'] for c in inspector.get_columns(table_name)}
        if column_name in existing:
            app.logger.info('Database migration: %s.%s was added concurrently', table_name, column_name)
            return False
        app.logger.exception('Database migration failed while adding %s.%s', table_name, column_name)
        raise

def run_schema_migrations():
    """Apply the known additive schema upgrades needed by the current application."""
    migrations = {
        'customer': [
            ('referred_by', 'VARCHAR(50)'),
            ('last_daily_login', 'DATE'),
            ('login_streak', 'INTEGER DEFAULT 1'),
            ('last_active_at', 'TIMESTAMP'),
        ],
        'order': [
            ('dining_option', "VARCHAR(20) DEFAULT 'DINE-IN'"),
        ],
        'promotion_tracker': [
            ('promo_cost', 'FLOAT DEFAULT 0.0'),
            ('is_visible', 'BOOLEAN DEFAULT TRUE'),
            ('portal_only', 'BOOLEAN DEFAULT FALSE'),
            ('description', 'TEXT'),
        ],
        'product': [
            ('cost', 'FLOAT DEFAULT 0.0'),
            ('allow_custom_amount', 'BOOLEAN DEFAULT FALSE'),
            ('minimum_order_amount', 'FLOAT'),
            ('option_schema', 'TEXT'),
            ('available_start_time', 'VARCHAR(10)'),
            ('available_end_time', 'VARCHAR(10)'),
        ],
        'order_item': [
            ('cost_price', 'FLOAT DEFAULT 0.0'),
            ('selected_options', 'TEXT'),
        ],
        'vault_drop': [
            ('cash_breakdown', 'TEXT'),
        ],
    }

    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    for table_name, columns in migrations.items():
        if table_name not in tables:
            continue
        for column_name, ddl_type in columns:
            _ensure_column(table_name, column_name, ddl_type)

    # Normalize data for columns that were introduced after initial deployments.
    with db.engine.begin() as conn:
        if 'customer' in tables:
            conn.execute(text("UPDATE customer SET login_streak = 1 WHERE login_streak IS NULL"))
        if 'promotion_tracker' in tables:
            conn.execute(text("UPDATE promotion_tracker SET is_visible = TRUE WHERE is_visible IS NULL"))
            conn.execute(text("UPDATE promotion_tracker SET portal_only = FALSE WHERE portal_only IS NULL"))
        if 'product' in tables:
            conn.execute(text("UPDATE product SET allow_custom_amount = FALSE WHERE allow_custom_amount IS NULL"))

def run_db_setup():
    global _DB_INITIALIZED
    if _DB_INITIALIZED:
        return
    try:
        db.create_all()
        run_schema_migrations()

        # Create bootstrap accounts only when they do not already exist. Never reset an existing PIN on restart.
        default_roles = [
            ('admin', os.environ.get('DEFAULT_ADMIN_PIN') or '1234', 'ADMIN'),
            ('cashier1', os.environ.get('DEFAULT_CASHIER_PIN') or '1111', 'CASHIER'),
        ]
        for username, pin, role in default_roles:
            existing = Staff.query.filter(db.func.lower(Staff.username) == username.lower()).first()
            if not existing:
                db.session.add(Staff(
                    username=username,
                    pin_hash=generate_password_hash(pin),
                    role=role,
                    active=True,
                ))
                if not os.environ.get('DEFAULT_ADMIN_PIN' if role == 'ADMIN' else 'DEFAULT_CASHIER_PIN'):
                    app.logger.warning('Created bootstrap %s account %r using the built-in first-run PIN. Change it in Admin immediately.', role, username)
        db.session.commit()

        ensure_default_promos()
        _DB_INITIALIZED = True
        app.logger.info('Database setup completed successfully.')
    except Exception:
        db.session.rollback()
        app.logger.exception('Database setup failed. Deployment/request should fail visibly instead of hiding schema errors.')
        raise

@app.before_request
def app_startup_and_session_handler():
    if not _DB_INITIALIZED:
        run_db_setup()

    # Customer logins may persist for up to 30 days. Staff sessions remain browser-session cookies
    # and are additionally protected by the explicit 8-hour inactivity check in the staff guards.
    session.permanent = bool(session.get('customer_id')) and not bool(session.get('admin_user') or session.get('cashier_user'))

    if 'customer_id' in session:
        try:
            cust = db.session.get(Customer, session['customer_id'])
            if cust and hasattr(cust, 'last_active_at'):
                cust.last_active_at = utc_now()
                db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.exception('Could not update customer last_active_at for customer_id=%s', session.get('customer_id'))

# ==================== HELPERS & GUARDS ====================

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or '127.0.0.1'

class OrderValidationError(ValueError):
    pass

def parse_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)

def parse_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)

def parse_product_option_schema(schema, strict=False):
    """Parse a compact product-option definition.

    Admin syntax examples:
        Sauce[]: Hot|Sweet; Flavor: Ube|Chocolate|Vanilla
        Sauce: Hot|Sweet

    A group name ending in [] is a checkbox group and allows one or more choices.
    A normal group is a single-choice group and is shown as radio buttons.
    Every configured group is required when the product is ordered. Choices do not
    change price; they only describe the selected preparation/flavor.
    """
    raw = str(schema or '').strip()
    if not raw:
        return []

    groups = []
    seen_groups = set()
    segments = [x.strip() for x in re.split(r'[;\n]+', raw) if x.strip()]
    if len(segments) > 6:
        raise OrderValidationError('A product can have at most 6 option groups.')

    for segment in segments:
        if ':' in segment:
            label, choices_raw = segment.split(':', 1)
        elif '=' in segment:
            label, choices_raw = segment.split('=', 1)
        else:
            if strict:
                raise OrderValidationError(
                    f"Invalid product option '{segment}'. Use Group: Choice1|Choice2."
                )
            continue

        label = re.sub(r'\s+', ' ', label.strip())
        multiple = False
        if label.endswith('[]'):
            multiple = True
            label = label[:-2].strip()
        label = label[:40]
        if not label:
            if strict:
                raise OrderValidationError('Every product option group needs a name.')
            continue
        key = label.casefold()
        if key in seen_groups:
            raise OrderValidationError(f"Duplicate product option group: {label}.")
        seen_groups.add(key)

        # Prefer | as the separator; allow commas as a convenient fallback.
        splitter = '|' if '|' in choices_raw else ','
        choices = []
        seen_choices = set()
        for value in choices_raw.split(splitter):
            value = re.sub(r'\s+', ' ', value.strip())[:60]
            if not value:
                continue
            vkey = value.casefold()
            if vkey not in seen_choices:
                seen_choices.add(vkey)
                choices.append(value)
        if len(choices) < 2:
            if strict:
                raise OrderValidationError(f"{label} needs at least 2 choices.")
            continue
        if len(choices) > 20:
            raise OrderValidationError(f"{label} can have at most 20 choices.")
        groups.append({'name': label, 'choices': choices, 'multiple': multiple})

    if strict and raw and not groups:
        raise OrderValidationError('Product options could not be read. Example: Sauce[]: Hot|Sweet; Flavor: Ube|Chocolate')
    return groups

def normalize_product_option_schema(schema):
    groups = parse_product_option_schema(schema, strict=bool(str(schema or '').strip()))
    return '; '.join(
        f"{g['name']}{'[]' if g.get('multiple') else ''}: {'|'.join(g['choices'])}"
        for g in groups
    ) or None

def validate_product_options(prod, raw_options):
    groups = parse_product_option_schema(getattr(prod, 'option_schema', None), strict=False)
    if not groups:
        if raw_options not in (None, '', {}, []):
            raise OrderValidationError(f'{prod.name} does not have selectable options.')
        return {}

    if isinstance(raw_options, str):
        raw_options = raw_options.strip()
        if not raw_options:
            raw_options = {}
        else:
            try:
                raw_options = json.loads(raw_options)
            except (TypeError, ValueError):
                raise OrderValidationError(f'Invalid option selection for {prod.name}.')
    if not isinstance(raw_options, dict):
        raise OrderValidationError(f'Please choose the required options for {prod.name}.')

    provided = {str(k).strip().casefold(): v for k, v in raw_options.items()}
    selected = {}
    allowed_group_keys = {g['name'].casefold() for g in groups}
    extras = set(provided) - allowed_group_keys
    if extras:
        raise OrderValidationError(f'Invalid option group submitted for {prod.name}.')

    for group in groups:
        label = group['name']
        value = provided.get(label.casefold())
        is_multiple = bool(group.get('multiple'))

        if is_multiple:
            values = value if isinstance(value, list) else ([value] if value not in (None, '') else [])
            canonical_values = []
            seen = set()
            for raw_value in values:
                value_text = re.sub(r'\s+', ' ', str(raw_value or '').strip())
                if not value_text:
                    continue
                canonical = next((c for c in group['choices'] if c.casefold() == value_text.casefold()), None)
                if canonical is None:
                    raise OrderValidationError(f'Invalid {label} choice for {prod.name}.')
                key = canonical.casefold()
                if key not in seen:
                    seen.add(key)
                    canonical_values.append(canonical)
            if not canonical_values:
                raise OrderValidationError(f'Please choose at least one {label} for {prod.name}.')
            selected[label] = canonical_values
        else:
            if isinstance(value, list):
                if len(value) != 1:
                    raise OrderValidationError(f'Please choose exactly one {label} for {prod.name}.')
                value = value[0]
            value_text = re.sub(r'\s+', ' ', str(value or '').strip())
            if not value_text:
                raise OrderValidationError(f'Please choose {label} for {prod.name}.')
            canonical = next((c for c in group['choices'] if c.casefold() == value_text.casefold()), None)
            if canonical is None:
                raise OrderValidationError(f'Invalid {label} choice for {prod.name}.')
            selected[label] = canonical
    return selected

def serialize_selected_options(options):
    return json.dumps(options or {}, ensure_ascii=False, separators=(',', ':')) if options else None

def option_summary(raw):
    if not raw:
        return ''
    data = raw
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            return raw
    if isinstance(data, dict):
        def fmt(v):
            if isinstance(v, list):
                return ' + '.join(str(x) for x in v)
            return str(v)
        return ' • '.join(f'{k}: {fmt(v)}' for k, v in data.items())
    return str(data)

app.jinja_env.filters['option_summary'] = option_summary

def is_valid_customer_pin(pin):
    return bool(pin) and len(pin) == 4 and pin.isdigit()

def mask_card_number(card_number):
    value = (card_number or '').strip()
    if not value:
        return 'Member'
    if len(value) <= 4:
        return '*' * len(value)
    return f"{value[:4]}****{value[-2:]}"

def customer_access_issue(cust):
    if not cust:
        return 'Customer account was not found.'
    status = (cust.card_status or 'ACTIVE').upper()
    if cust.card_expires_at and ph_today() > cust.card_expires_at:
        return 'Your rewards card has expired. Please ask staff to renew it.'
    if status != 'ACTIVE':
        if status == 'LOCKED':
            return 'Your rewards account is locked. Please ask staff for assistance.'
        if status == 'EXPIRED':
            return 'Your rewards card has expired. Please ask staff to renew it.'
        return f'Your rewards account is currently {status.lower()}.'
    return None

def get_customer_by_identifier(identifier):
    value = (identifier or '').strip()
    if not value:
        return None
    return Customer.query.filter(
        (Customer.contact == value) | (db.func.lower(Customer.card_number) == value.lower())
    ).first()

def generate_unique_card_number(customer_id=None):
    """Continue the MFH sequence without random collisions."""
    highest = 0
    for (card,) in db.session.query(Customer.card_number).filter(Customer.card_number.isnot(None)).all():
        match = re.fullmatch(r'MFH-(\d+)', card or '', flags=re.IGNORECASE)
        if match:
            highest = max(highest, int(match.group(1)))
    number = max(highest + 1, parse_int(customer_id, 0) or 1)
    while True:
        width = 4 if number <= 9999 else 6
        candidate = f"MFH-{number:0{width}d}"
        if not Customer.query.filter(db.func.lower(Customer.card_number) == candidate.lower()).first():
            return candidate
        number += 1

def customer_available_credit(cust, include_pending=True):
    limit = max(0.0, parse_float(cust.credit_limit, 0.0))
    used = max(0.0, parse_float(cust.outstanding_ar, 0.0))
    if include_pending:
        pending = db.session.query(db.func.coalesce(db.func.sum(Order.total_amount), 0.0)).filter(
            Order.customer_id == cust.id,
            Order.payment_method == 'CREDIT',
            Order.status == 'VERIFICATION',
        ).scalar() or 0.0
        used += float(pending)
    return max(0.0, limit - used)

def validate_and_lock_cart(raw_items, require_available=True, allow_cashier_custom_amount=False):
    """Validate quantities, options, products and stock using server-side truth.

    Products may define required sub-options such as Sauce (Hot/Sweet) or Flavor.
    The same base product can appear as multiple cart lines when option choices differ.
    """
    if not isinstance(raw_items, list) or not raw_items:
        raise OrderValidationError('No items were selected.')

    raw_entries = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise OrderValidationError('Invalid cart item.')
        product_id = parse_int(raw.get('product_id'), 0)
        quantity = parse_int(raw.get('quantity'), 0)
        if product_id <= 0:
            raise OrderValidationError('A cart item has an invalid product ID.')
        if quantity < 1:
            raise OrderValidationError('Item quantity must be at least 1.')
        if quantity > 999:
            raise OrderValidationError('Item quantity is too large.')

        requested_price = None
        if allow_cashier_custom_amount and raw.get('unit_price') not in (None, ''):
            requested_price = round(parse_float(raw.get('unit_price'), -1.0), 2)
            if requested_price <= 0:
                raise OrderValidationError('Specific amount must be greater than ₱0.00.')

        raw_entries.append({
            'product_id': product_id,
            'quantity': quantity,
            'requested_price': requested_price,
            'raw_options': raw.get('options', {}),
        })

    product_cache = {}
    combined = {}
    aggregate_qty = {}

    for entry in raw_entries:
        product_id = entry['product_id']
        prod = product_cache.get(product_id)
        if prod is None:
            stmt = db.select(Product).where(Product.id == product_id)
            if db.engine.dialect.name != 'sqlite':
                stmt = stmt.with_for_update()
            prod = db.session.execute(stmt).scalar_one_or_none()
            if not prod:
                raise OrderValidationError(f'Product #{product_id} no longer exists.')
            product_cache[product_id] = prod

        if not prod.is_active:
            raise OrderValidationError(f'{prod.name} is currently inactive.')
        if require_available and not is_product_available_now(prod):
            raise OrderValidationError(f'{prod.name} is not available at this time.')

        base_price = round(max(0.0, parse_float(prod.price, 0.0)), 2)
        if base_price <= 0:
            raise OrderValidationError(f'{prod.name} has an invalid selling price.')
        unit_price = base_price

        requested_price = entry['requested_price']
        if requested_price is not None:
            if not allow_cashier_custom_amount:
                raise OrderValidationError('Specific amounts are only available at the Cashier POS.')
            if not bool(getattr(prod, 'allow_custom_amount', False)):
                raise OrderValidationError(f'{prod.name} does not allow a specific cashier amount.')
            min_amount = round(parse_float(getattr(prod, 'minimum_order_amount', None), base_price), 2)
            if min_amount <= 0:
                min_amount = base_price
            if requested_price + 0.004 < min_amount:
                raise OrderValidationError(
                    f'{prod.name} cannot be sold below its ₱{min_amount:,.2f} minimum order amount.'
                )
            unit_price = requested_price

        selected_options = validate_product_options(prod, entry['raw_options'])
        selected_json = serialize_selected_options(selected_options)
        identity = (product_id, round(unit_price, 2), selected_json or '')
        if identity in combined:
            combined[identity]['quantity'] += entry['quantity']
            combined[identity]['subtotal'] = combined[identity]['unit_price'] * combined[identity]['quantity']
        else:
            cost_price = max(0.0, parse_float(prod.cost, 0.0))
            combined[identity] = {
                'product': prod,
                'quantity': entry['quantity'],
                'unit_price': unit_price,
                'cost_price': cost_price,
                'subtotal': unit_price * entry['quantity'],
                'selected_options': selected_options,
                'selected_options_json': selected_json,
            }
        aggregate_qty[product_id] = aggregate_qty.get(product_id, 0) + entry['quantity']

    for product_id, total_qty in aggregate_qty.items():
        prod = product_cache[product_id]
        stock = max(0, parse_int(prod.stock, 0))
        if stock < total_qty:
            raise OrderValidationError(f'Not enough stock for {prod.name}. Available: {stock}.')

    return list(combined.values())

def reserve_cart_stock(lines):
    for line in lines:
        line['product'].stock = parse_int(line['product'].stock, 0) - line['quantity']

def cart_subtotal(lines):
    return sum(line['subtotal'] for line in lines)

def staff_session_valid():
    raw = session.get('_staff_last_activity')
    if not raw:
        return False
    try:
        last = datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        return False
    now = utc_now()
    if now - last > STAFF_SESSION_TIMEOUT:
        return False
    session['_staff_last_activity'] = now.isoformat()
    return True

def clear_staff_session():
    for key in ('admin_id', 'admin_user', 'cashier_id', 'cashier_user', '_staff_last_activity'):
        session.pop(key, None)

def get_store_settings():
    try:
        settings = {row.key: row.value for row in StoreSetting.query.all()}
    except Exception:
        app.logger.exception('Store settings query failed; using safe defaults for this request')
        settings = {}
    defaults = {
        'store_open_time': '08:00',
        'store_close_time': '21:00',
        'delivery_open_time': '08:00',
        'delivery_close_time': '20:00',
        'is_store_open': 'true',
        'is_delivery_enabled': 'true'
    }
    for k, v in defaults.items():
        settings.setdefault(k, v)
    return settings

def check_operating_status():
    s = get_store_settings()
    now_ph = ph_now().time()

    def parse_t(val, fallback):
        try:
            return datetime.strptime(val, '%H:%M').time()
        except Exception:
            return fallback

    store_open = parse_t(s.get('store_open_time', '08:00'), time(8, 0))
    store_close = parse_t(s.get('store_close_time', '21:00'), time(21, 0))
    del_open = parse_t(s.get('delivery_open_time', '08:00'), time(8, 0))
    del_close = parse_t(s.get('delivery_close_time', '20:00'), time(20, 0))

    is_store_active = (s.get('is_store_open') == 'true') and (store_open <= now_ph <= store_close)
    is_delivery_active = (s.get('is_delivery_enabled') == 'true') and (del_open <= now_ph <= del_close) and is_store_active

    return {
        'store_open': is_store_active,
        'delivery_open': is_delivery_active,
        'settings': s,
        'current_time': now_ph.strftime('%I:%M %p')
    }

def is_product_available_now(prod):
    if not prod.is_active:
        return False
    if not getattr(prod, 'available_start_time', None) or not getattr(prod, 'available_end_time', None):
        return True
    try:
        now_ph = ph_now().time()
        start = datetime.strptime(prod.available_start_time, '%H:%M').time()
        end = datetime.strptime(prod.available_end_time, '%H:%M').time()
        if start <= end:
            return start <= now_ph <= end
        return now_ph >= start or now_ph <= end
    except Exception:
        return True

def ensure_default_promos():
    try:
        deal1 = PromotionTracker.query.filter_by(promo_code='BURGER_FRIES_50').first()
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
            ))

        deal2 = PromotionTracker.query.filter_by(promo_code='BEEFY_NACHOS_75').first()
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
            ))

        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception('Could not ensure default promotions')
        raise

@app.template_filter('ph_datetime')
def ph_datetime_filter(value, fmt='%b %d, %Y - %I:%M %p'):
    local_value = utc_naive_to_ph(value)
    return local_value.strftime(fmt) if local_value else ''

def track_portal_event(event_type, source=None, customer_id=None):
    """Best-effort portal/QR analytics. Never block a customer action if tracking fails."""
    try:
        db.session.add(PortalEvent(
            source=(source or session.get('portal_source') or 'direct')[:30],
            event_type=str(event_type)[:50],
            customer_id=customer_id,
        ))
    except Exception:
        app.logger.exception('Could not queue portal event %s', event_type)

def _parse_campaign_time(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%H:%M').time()
    except (TypeError, ValueError):
        return None

def bonus_campaign_applies(campaign, order=None, moment=None):
    if not campaign.is_active:
        return False
    if order and order.created_at:
        local_dt = utc_naive_to_ph(order.created_at)
    else:
        local_dt = moment or ph_now()
    day = local_dt.date()
    local_time = local_dt.time().replace(tzinfo=None)

    if campaign.start_date and day < campaign.start_date:
        return False
    if campaign.end_date and day > campaign.end_date:
        return False

    if campaign.weekdays:
        allowed = {x.strip() for x in campaign.weekdays.split(',') if x.strip()}
        if allowed and str(local_dt.weekday()) not in allowed:
            return False

    start = _parse_campaign_time(campaign.start_time)
    end = _parse_campaign_time(campaign.end_time)
    if start and end:
        if start <= end:
            if not (start <= local_time <= end):
                return False
        elif not (local_time >= start or local_time <= end):
            return False
    elif start and local_time < start:
        return False
    elif end and local_time > end:
        return False

    if order and (order.total_amount or 0.0) + 1e-9 < (campaign.min_spend or 0.0):
        return False
    return True

def get_active_bonus_campaigns(moment=None):
    campaigns = BonusCampaign.query.filter_by(is_active=True).order_by(BonusCampaign.created_at.desc()).all()
    return [c for c in campaigns if bonus_campaign_applies(c, moment=moment or ph_now())]

def award_active_bonus_campaigns(cust, order):
    if not cust or not order or order.id is None or order.status != 'COMPLETED':
        return 0.0
    total_bonus = 0.0
    campaigns = BonusCampaign.query.filter_by(is_active=True).all()
    for campaign in campaigns:
        if not bonus_campaign_applies(campaign, order=order):
            continue
        existing = BonusCampaignClaim.query.filter_by(campaign_id=campaign.id, order_id=order.id).first()
        if existing:
            continue
        fixed_bonus = max(0.0, float(campaign.bonus_points or 0.0))
        multiplier = max(1.0, float(campaign.points_multiplier or 1.0))
        base_points = max(0, int((order.total_amount or 0.0) // 30))
        multiplier_bonus = max(0.0, (multiplier - 1.0) * base_points)
        bonus = fixed_bonus + multiplier_bonus
        if bonus <= 0:
            continue
        cust.points_balance = (cust.points_balance or 0.0) + bonus
        db.session.add(BonusCampaignClaim(
            campaign_id=campaign.id,
            customer_id=cust.id,
            order_id=order.id,
            points_awarded=bonus,
        ))
        db.session.add(RewardLedger(
            customer_id=cust.id,
            points_change=bonus,
            reason=f"Bonus Campaign: {campaign.title} / Order #{order.id}",
        ))
        total_bonus += bonus
    return total_bonus

def award_referral_first_purchase(cust, order):
    """Reward a valid referral only after the referred member completes a paid purchase."""
    if not cust or not order or not cust.referred_by or order.status != 'COMPLETED' or not order.payment_verified:
        return 0.0, 0.0
    if ReferralReward.query.filter_by(referred_customer_id=cust.id).first():
        return 0.0, 0.0

    referrer = get_customer_by_identifier(cust.referred_by)
    if not referrer or referrer.id == cust.id or customer_access_issue(referrer):
        return 0.0, 0.0

    # Older versions awarded the referrer +2 immediately on signup. Detect that ledger entry
    # so existing accounts are never rewarded twice after this upgrade.
    legacy_reason = f"Referral Bonus: Invited {cust.name}"
    already_paid_referrer = RewardLedger.query.filter_by(customer_id=referrer.id, reason=legacy_reason).first() is not None
    referrer_points = 0.0 if already_paid_referrer else 2.0
    referred_points = 2.0

    if referrer_points:
        referrer.points_balance = (referrer.points_balance or 0.0) + referrer_points
        db.session.add(RewardLedger(
            customer_id=referrer.id,
            points_change=referrer_points,
            reason=f"Referral First-Purchase Bonus: {cust.name}",
        ))
    cust.points_balance = (cust.points_balance or 0.0) + referred_points
    db.session.add(RewardLedger(
        customer_id=cust.id,
        points_change=referred_points,
        reason=f"Referral Welcome Purchase Bonus / Order #{order.id}",
    ))
    db.session.add(ReferralReward(
        referrer_customer_id=referrer.id,
        referred_customer_id=cust.id,
        first_order_id=order.id,
        referrer_points=referrer_points,
        referred_points=referred_points,
    ))
    return referrer_points, referred_points

def apply_member_marketing_rewards(cust, order):
    """Apply non-base marketing rewards to a completed, paid member transaction."""
    if not cust or not order or order.status != 'COMPLETED' or not order.payment_verified:
        return {'bonus_points': 0.0, 'referral_member_points': 0.0, 'referrer_points': 0.0}
    bonus = award_active_bonus_campaigns(cust, order)
    referrer_pts, referred_pts = award_referral_first_purchase(cust, order)
    return {
        'bonus_points': bonus,
        'referral_member_points': referred_pts,
        'referrer_points': referrer_pts,
    }

def reverse_member_marketing_rewards_for_order(order):
    """Reverse bonus/referral points tied to a completed order before reassign/delete."""
    if not order or order.id is None:
        return

    for claim in BonusCampaignClaim.query.filter_by(order_id=order.id).all():
        cust = db.session.get(Customer, claim.customer_id)
        if cust and claim.points_awarded:
            cust.points_balance = max(0.0, (cust.points_balance or 0.0) - claim.points_awarded)
            db.session.add(RewardLedger(
                customer_id=cust.id,
                points_change=-claim.points_awarded,
                reason=f"Reversed Bonus Campaign / Order #{order.id}",
            ))
        db.session.delete(claim)

    referral = ReferralReward.query.filter_by(first_order_id=order.id).first()
    if referral:
        referred = db.session.get(Customer, referral.referred_customer_id)
        referrer = db.session.get(Customer, referral.referrer_customer_id)
        if referred and referral.referred_points:
            referred.points_balance = max(0.0, (referred.points_balance or 0.0) - referral.referred_points)
            db.session.add(RewardLedger(
                customer_id=referred.id,
                points_change=-referral.referred_points,
                reason=f"Reversed Referral Purchase Bonus / Order #{order.id}",
            ))
        if referrer and referral.referrer_points:
            referrer.points_balance = max(0.0, (referrer.points_balance or 0.0) - referral.referrer_points)
            db.session.add(RewardLedger(
                customer_id=referrer.id,
                points_change=-referral.referrer_points,
                reason=f"Reversed Referral Bonus / Order #{order.id}",
            ))
        db.session.delete(referral)

@app.context_processor
def inject_globals():
    try:
        setting = StoreSetting.query.filter_by(key='logo_url').first()
        logo = setting.value if setting else '/static/logo.png'
    except Exception:
        app.logger.exception('Logo setting query failed; using /static/logo.png fallback')
        logo = '/static/logo.png'
    status = check_operating_status()
    return dict(store_logo=logo, status=status, mask_card_number=mask_card_number, product_option_groups=parse_product_option_schema)

def _staff_auth_failure(target, message):
    """Return JSON for fetch/API calls and a normal login redirect for browser forms."""
    clear_staff_session()
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': message}), 401
    flash(message, 'info')
    return redirect(url_for('staff_login', target=target))

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_user') or not staff_session_valid():
            return _staff_auth_failure('admin', 'Admin session expired. Please log in again.')
        return f(*args, **kwargs)
    return decorated

def require_cashier(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not (session.get('cashier_user') or session.get('admin_user')) or not staff_session_valid():
            return _staff_auth_failure('cashier', 'Staff session expired. Please log in again.')
        return f(*args, **kwargs)
    return decorated

# ==================== REAL-TIME POLLING API ====================

@app.route('/api/queue-counts')
def api_queue_counts():
    try:
        pending_cashier = Order.query.filter_by(status="VERIFICATION").count()
        return jsonify({'pending_cashier': pending_cashier})
    except Exception:
        app.logger.exception('Queue-count query failed')
        return jsonify({'error': 'Queue data is temporarily unavailable.'}), 500

# ==================== STOREFRONT ====================

@app.route('/')
def store_catalog():
    try:
        ip = get_client_ip()
        v = SiteVisitor.query.filter_by(ip_address=ip).first()
        if not v:
            db.session.add(SiteVisitor(ip_address=ip, visit_count=1))
        else:
            v.visit_count = (v.visit_count or 0) + 1
        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception('Storefront visitor tracking update failed')

    try:
        unique_visitors = SiteVisitor.query.count()
        total_accumulated_visits = db.session.query(db.func.coalesce(db.func.sum(SiteVisitor.visit_count), 0)).scalar() or unique_visitors
    except Exception:
        app.logger.exception('Storefront visitor metrics query failed')
        unique_visitors = 0
        total_accumulated_visits = 0

    categories = Category.query.all()
    all_active_products = Product.query.filter_by(is_active=True).all()
    available_products = [p for p in all_active_products if is_product_available_now(p)]

    featured = [p for p in available_products if p.is_featured]
    top_sellers = [p for p in available_products if p.is_top_seller]
    products = sorted(available_products, key=lambda x: (-(x.total_likes or 0), x.id))

    liked_ids = {pl.product_id for pl in ProductLike.query.filter_by(ip_address=get_client_ip()).all()}
    delivery_zones = DeliveryZone.query.filter_by(is_active=True).all()
    status = check_operating_status()
    active_promos = PromotionTracker.query.filter_by(is_active=True, is_visible=True, portal_only=False).all()
    active_promos = [p for p in active_promos if not p.created_at or (utc_now() - p.created_at).days <= 3]

    cust = None
    credit_available = 0.0
    if 'customer_id' in session:
        cust = Customer.query.get(session['customer_id'])
        if cust and cust.is_credit_eligible and not customer_access_issue(cust):
            credit_available = customer_available_credit(cust, include_pending=True)

    return render_template('store_catalog.html', 
                           categories=categories, 
                           featured=featured, 
                           top_sellers=top_sellers, 
                           products=products, 
                           liked_ids=liked_ids, 
                           delivery_zones=delivery_zones, 
                           active_promos=active_promos, 
                           cust=cust, 
                           status=status, 
                           unique_visitors=unique_visitors, 
                           total_accumulated_visits=total_accumulated_visits,
                           credit_available=credit_available)

@app.route('/promo/burger-deal')
def promo_burger_deal():
    promo = PromotionTracker.query.filter_by(promo_code='BURGER_FRIES_50').first()
    if promo:
        promo.page_views = (promo.page_views or 0) + 1
        db.session.commit()
    return render_template('promo_burger_deal.html')

@app.route('/promo/beefy-nachos')
def promo_beefy_nachos():
    promo = PromotionTracker.query.filter_by(promo_code='BEEFY_NACHOS_75').first()
    if promo:
        promo.page_views = (promo.page_views or 0) + 1
        db.session.commit()
    return render_template('promo_beefy_nachos.html')

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    prod = Product.query.get_or_404(product_id)
    ip = get_client_ip()
    liked = bool(ProductLike.query.filter_by(product_id=product_id, ip_address=ip).first())
    return render_template('product_detail.html', prod=prod, liked=liked)

@app.route('/api/toggle-like/<int:product_id>', methods=['POST'])
def api_toggle_like(product_id):
    ip = get_client_ip()
    cust_id = session.get('customer_id')
    prod = Product.query.get_or_404(product_id)

    existing = ProductLike.query.filter_by(product_id=product_id, ip_address=ip).first()
    if existing:
        db.session.delete(existing)
        prod.total_likes = max(0, (prod.total_likes or 0) - 1)
        db.session.commit()
        return jsonify({'liked': False, 'total_likes': prod.total_likes})
    else:
        db.session.add(ProductLike(product_id=product_id, ip_address=ip, customer_id=cust_id))
        prod.total_likes = (prod.total_likes or 0) + 1
        db.session.commit()
        return jsonify({'liked': True, 'total_likes': prod.total_likes})

@app.route('/api/add-comment/<int:product_id>', methods=['POST'])
def api_add_comment(product_id):
    ip = get_client_ip()
    cust_id = session.get('customer_id')
    data = request.get_json() or {}
    text_content = data.get('comment', '').strip()
    if not text_content:
        return jsonify({'success': False, 'message': 'Comment cannot be empty.'}), 400

    name = f"Guest ({ip})"
    if cust_id:
        cust = Customer.query.get(cust_id)
        if cust:
            name = cust.name

    comment = ProductComment(product_id=product_id, customer_id=cust_id, author_name=name, ip_address=ip, comment_text=text_content)
    db.session.add(comment)
    db.session.commit()
    return jsonify({'success': True, 'author': name, 'comment': text_content, 'created_at': 'Just now'})

@app.route('/api/storefront-checkout', methods=['POST'])
def api_storefront_checkout():
    if 'customer_id' not in session:
        return jsonify({'success': False, 'message': 'Registration / Login is required. No guest checkout.'}), 403

    cust = db.session.get(Customer, session['customer_id'])
    issue = customer_access_issue(cust)
    if issue:
        return jsonify({'success': False, 'message': issue}), 403

    data = request.get_json() or {}
    order_type = str(data.get('order_type', 'PICKUP')).upper()
    dining_opt = str(data.get('dining_option', 'TAKEOUT')).upper()
    pay_method = str(data.get('payment_method', 'CASH')).upper()
    notes = str(data.get('notes', '')).strip() or 'None'
    target_time = str(data.get('target_time', '')).strip()
    zone_id = data.get('delivery_zone_id')
    landmark = str(data.get('landmark', '')).strip()
    delivery_address = str(data.get('delivery_address', '')).strip()
    gcash_ref = str(data.get('gcash_ref', '')).strip()
    fb = str(data.get('fb_messenger', '')).strip()

    if order_type not in {'PICKUP', 'DELIVERY'}:
        return jsonify({'success': False, 'message': 'Invalid order type.'}), 400
    if pay_method not in {'CASH', 'GCASH', 'CREDIT'}:
        return jsonify({'success': False, 'message': 'Invalid payment method.'}), 400

    status = check_operating_status()
    if order_type == 'PICKUP' and not status['store_open']:
        return jsonify({'success': False, 'message': 'Store ordering is currently closed.'}), 400
    if order_type == 'DELIVERY' and not status['delivery_open']:
        return jsonify({'success': False, 'message': 'Barangay delivery is currently unavailable/closed.'}), 400
    if not target_time:
        return jsonify({'success': False, 'message': 'Please provide your target time.'}), 400

    delivery_fee = 0.0
    final_address = delivery_address
    final_landmark = landmark
    if order_type == 'DELIVERY':
        dining_opt = 'DELIVERY'
        if not zone_id and (not landmark or not delivery_address):
            return jsonify({'success': False, 'message': 'Please choose a Barangay Delivery Zone or provide address info.'}), 400
        if zone_id:
            zone = db.session.get(DeliveryZone, parse_int(zone_id, 0))
            if not zone or not zone.is_active:
                return jsonify({'success': False, 'message': 'The selected delivery zone is unavailable.'}), 400
            delivery_fee = max(0.0, parse_float(zone.rate, 0.0))
            final_address = f"Barangay: {zone.barangay} ({zone.place_name})"
            final_landmark = landmark or zone.note or 'Designated Delivery Spot'
    else:
        dining_opt = 'TAKEOUT' if dining_opt not in {'DINE-IN', 'TAKEOUT'} else dining_opt

    if pay_method == 'CREDIT' and not cust.is_credit_eligible:
        return jsonify({'success': False, 'message': 'Your account is not authorized for A/R Credit.'}), 403
    if pay_method in {'GCASH', 'CREDIT'} and not fb:
        return jsonify({'success': False, 'message': 'Facebook messenger link is required for evaluation.'}), 400
    if pay_method == 'GCASH' and (len(gcash_ref) != 6 or not gcash_ref.isdigit()):
        return jsonify({'success': False, 'message': 'Please input the 6-digit GCash Reference Number.'}), 400

    try:
        lines = validate_and_lock_cart(data.get('items', []), require_available=True)
        subtotal = cart_subtotal(lines)
        total = subtotal + delivery_fee

        if pay_method == 'CREDIT':
            available_credit = customer_available_credit(cust, include_pending=True)
            if total > available_credit + 1e-9:
                return jsonify({
                    'success': False,
                    'message': f'Credit limit exceeded. Available credit: ₱{available_credit:,.2f}.'
                }), 400

        change_for = parse_float(data.get('change_for'), 0.0) if pay_method == 'CASH' else 0.0
        if pay_method == 'CASH' and change_for and change_for < total:
            return jsonify({'success': False, 'message': 'Cash bill cannot be less than the order total.'}), 400

        order = Order(
            order_type=order_type,
            dining_option=dining_opt,
            customer_id=cust.id,
            customer_name=cust.name,
            contact_number=cust.contact,
            fb_messenger=fb or cust.fb_messenger,
            delivery_address=final_address if order_type == 'DELIVERY' else None,
            landmark=final_landmark if order_type == 'DELIVERY' else None,
            pickup_time=target_time if order_type == 'PICKUP' else None,
            target_time=target_time,
            change_for=change_for if pay_method == 'CASH' and change_for > 0 else None,
            gcash_ref=gcash_ref if pay_method == 'GCASH' else None,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total_amount=total,
            payment_method=pay_method,
            payment_verified=False,
            status='VERIFICATION',
            notes=notes,
        )
        db.session.add(order)
        db.session.flush()

        for line in lines:
            prod = line['product']
            db.session.add(OrderItem(
                order_id=order.id,
                product_id=prod.id,
                product_name=prod.name,
                unit_price=line['unit_price'],
                cost_price=line['cost_price'],
                quantity=line['quantity'],
                subtotal=line['subtotal'],
                selected_options=line.get('selected_options_json'),
            ))
        reserve_cart_stock(lines)
        db.session.commit()
        return jsonify({'success': True, 'order_id': order.id, 'total': total})
    except OrderValidationError as exc:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        db.session.rollback()
        app.logger.exception('Storefront checkout failed for customer_id=%s', cust.id)
        return jsonify({'success': False, 'message': 'Checkout failed due to a server error. No order was recorded.'}), 500

# ==================== TABLET KIOSK ENDPOINTS ====================

@app.route('/tablet')
def tablet_kiosk():
    categories = Category.query.all()
    all_active_products = Product.query.filter_by(is_active=True).all()
    available_products = [p for p in all_active_products if is_product_available_now(p)]
    return render_template('tablet.html', categories=categories, products=available_products)

@app.route('/api/tablet-checkout', methods=['POST'])
def api_tablet_checkout():
    data = request.get_json() or {}
    dining_opt = str(data.get('dining_option', 'DINE-IN')).upper()
    if dining_opt not in {'DINE-IN', 'TAKEOUT'}:
        dining_opt = 'DINE-IN'
    pay_method = str(data.get('payment_method', 'CASH')).upper()
    if pay_method not in {'CASH', 'GCASH'}:
        return jsonify({'success': False, 'message': 'Invalid kiosk payment method.'}), 400
    notes = str(data.get('notes', 'Tablet Self-Order')).strip() or 'Tablet Self-Order'

    cust = None
    member_identifier = str(data.get('member_identifier', '')).strip()
    member_pin = str(data.get('member_pin', '')).strip()
    if member_identifier or member_pin:
        if not member_identifier or not member_pin:
            return jsonify({'success': False, 'message': 'Enter both member mobile/card ID and 4-digit PIN, or leave both blank for guest checkout.'}), 400
        if not is_valid_customer_pin(member_pin):
            return jsonify({'success': False, 'message': 'Member PIN must be exactly 4 digits.'}), 400
        cust = get_customer_by_identifier(member_identifier)
        if not cust or not check_password_hash(cust.pin_hash, member_pin):
            return jsonify({'success': False, 'message': 'Invalid member ID/mobile number or PIN.'}), 403
        issue = customer_access_issue(cust)
        if issue:
            return jsonify({'success': False, 'message': issue}), 403

    try:
        lines = validate_and_lock_cart(data.get('items', []), require_available=True)
        subtotal = cart_subtotal(lines)
        order = Order(
            order_type='TABLET',
            dining_option=dining_opt,
            customer_id=cust.id if cust else None,
            customer_name=cust.name if cust else 'Tablet Kiosk Guest',
            contact_number=cust.contact if cust else 'Kiosk',
            subtotal=subtotal,
            delivery_fee=0.0,
            total_amount=subtotal,
            payment_method=pay_method,
            payment_verified=False,
            status='VERIFICATION',
            notes=notes,
        )
        db.session.add(order)
        db.session.flush()

        for line in lines:
            prod = line['product']
            db.session.add(OrderItem(
                order_id=order.id,
                product_id=prod.id,
                product_name=prod.name,
                unit_price=line['unit_price'],
                cost_price=line['cost_price'],
                quantity=line['quantity'],
                subtotal=line['subtotal'],
                selected_options=line.get('selected_options_json'),
            ))
        reserve_cart_stock(lines)
        db.session.commit()
        return jsonify({
            'success': True,
            'order_id': order.id,
            'total': subtotal,
            'member_name': cust.name if cust else None,
        })
    except OrderValidationError as exc:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        db.session.rollback()
        app.logger.exception('Tablet checkout failed')
        return jsonify({'success': False, 'message': 'Server error. No kiosk order was recorded.'}), 500

# ==================== CASHIER TERMINAL & CLAIM DISPATCH ====================

@app.route('/pos/cashier')
@require_cashier
def cashier_terminal():
    categories = Category.query.all()
    # Cashier is an internal staff terminal, so show every active product even
    # when its public/tablet availability window is currently closed.
    products = Product.query.filter_by(is_active=True).order_by(Product.id.asc()).all()

    # These are core cashier queries. Do not hide database/schema failures behind empty panels.
    pending_orders = Order.query.filter_by(status='VERIFICATION').order_by(Order.created_at.asc()).all()
    completed_orders = Order.query.filter_by(status='COMPLETED').order_by(Order.created_at.desc()).limit(15).all()
    unpaid_collections = Order.query.filter_by(is_unpaid=True).order_by(Order.created_at.desc()).all()

    staff_list = Staff.query.all()
    customers_list = Customer.query.order_by(Customer.name.asc()).all()
    two_mins_ago = utc_now() - timedelta(minutes=2)
    online_customers = Customer.query.filter(Customer.last_active_at >= two_mins_ago).order_by(Customer.last_active_at.desc()).all()
    credit_customers = Customer.query.filter(Customer.outstanding_ar > 0).order_by(Customer.outstanding_ar.desc()).all()

    start_today, next_day = ph_day_utc_bounds()
    today_expenses = Expense.query.filter(Expense.created_at >= start_today, Expense.created_at < next_day).order_by(Expense.created_at.desc()).all()
    today_drops = VaultDrop.query.filter(VaultDrop.created_at >= start_today, VaultDrop.created_at < next_day).order_by(VaultDrop.drop_number.asc()).all()
    today_change_funds = ChangeFund.query.filter(ChangeFund.created_at >= start_today, ChangeFund.created_at < next_day).order_by(ChangeFund.created_at.desc()).all()
    next_drop_num = len(today_drops) + 1
    active_bonus_campaigns = get_active_bonus_campaigns()

    return render_template(
        'cashier_pos.html',
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
        next_drop_num=next_drop_num,
        active_bonus_campaigns=active_bonus_campaigns,
    )

@app.route('/pos/direct-sale', methods=['POST'])
@require_cashier
def cashier_direct_sale():
    data = request.get_json() or {}
    cust_type = str(data.get('customer_type', 'WALKIN')).upper()
    reg_id = data.get('registered_customer_id')
    dining_opt = str(data.get('dining_option', 'DINE-IN')).upper()
    pay_method = str(data.get('payment_method', 'CASH')).upper()
    cust_name = str(data.get('customer_name', 'Counter Walk-in')).strip() or 'Counter Walk-in'
    notes = str(data.get('notes', 'Cashier Counter POS Sale')).strip() or 'Cashier Counter POS Sale'
    change_for = parse_float(data.get('change_for'), 0.0)

    if dining_opt not in {'DINE-IN', 'TAKEOUT'}:
        return jsonify({'success': False, 'message': 'Invalid dining option.'}), 400
    if pay_method not in {'CASH', 'GCASH'}:
        return jsonify({'success': False, 'message': 'Direct paid sales support Cash or GCash.'}), 400

    try:
        lines = validate_and_lock_cart(data.get('items', []), require_available=False, allow_cashier_custom_amount=True)
        subtotal = cart_subtotal(lines)
        if pay_method == 'CASH' and change_for and change_for < subtotal:
            raise OrderValidationError('Cash bill cannot be less than the sale total.')

        cust = None
        points_earned = 0
        contact = 'N/A'
        if cust_type == 'REGISTERED':
            cust = db.session.get(Customer, parse_int(reg_id, 0))
            if not cust:
                raise OrderValidationError('Please select a valid registered member.')
            issue = customer_access_issue(cust)
            if issue:
                raise OrderValidationError(issue)
            cust_name = cust.name
            contact = cust.contact
            cust.accumulated_spend = (cust.accumulated_spend or 0.0) + subtotal
            points_earned = int(subtotal // 30)
            if points_earned > 0:
                cust.points_balance = (cust.points_balance or 0.0) + points_earned
                db.session.add(RewardLedger(
                    customer_id=cust.id,
                    points_change=points_earned,
                    reason=f'Counter POS Sale (₱{subtotal:,.2f})',
                ))

        order = Order(
            order_type='COUNTER_SALE',
            dining_option=dining_opt,
            customer_id=cust.id if cust else None,
            customer_name=cust_name,
            contact_number=contact,
            subtotal=subtotal,
            delivery_fee=0.0,
            total_amount=subtotal,
            payment_method=pay_method,
            payment_verified=True,
            change_for=change_for if change_for > 0 else None,
            status='COMPLETED',
            notes=notes,
        )
        db.session.add(order)
        db.session.flush()

        for line in lines:
            prod = line['product']
            db.session.add(OrderItem(
                order_id=order.id,
                product_id=prod.id,
                product_name=prod.name,
                unit_price=line['unit_price'],
                cost_price=line['cost_price'],
                quantity=line['quantity'],
                subtotal=line['subtotal'],
                selected_options=line.get('selected_options_json'),
            ))
        reserve_cart_stock(lines)
        marketing = apply_member_marketing_rewards(cust, order) if cust else {'bonus_points': 0.0, 'referral_member_points': 0.0, 'referrer_points': 0.0}
        db.session.commit()
        return jsonify({
            'success': True,
            'order_id': order.id,
            'total': subtotal,
            'points_earned': points_earned,
            'bonus_points': marketing['bonus_points'],
            'referral_points': marketing['referral_member_points'],
            'member_balance': (cust.points_balance or 0.0) if cust else None,
        })
    except OrderValidationError as exc:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(exc)}), 400
    except Exception:
        db.session.rollback()
        app.logger.exception('Cashier direct sale failed')
        return jsonify({'success': False, 'message': 'Sale failed due to a server error. Nothing was recorded.'}), 500

@app.route('/pos/claim-promo', methods=['POST'])
@require_cashier
def cashier_claim_promo():
    promo_code = request.form.get('promo_code', 'BURGER_FRIES_50')
    reg_id = request.form.get('registered_customer_id')
    dining_opt = request.form.get('dining_option', 'DINE-IN').upper()
    pay_method = request.form.get('payment_method', 'CASH').upper()
    
    promo = PromotionTracker.query.filter_by(promo_code=promo_code).first()
    if not promo or not promo.is_active:
        flash("Promotion deal is not active or could not be found.", "error")
        return redirect(url_for('cashier_terminal'))
    if dining_opt not in {'DINE-IN', 'TAKEOUT'}:
        flash('Invalid dining option.', 'error')
        return redirect(url_for('cashier_terminal'))
    if pay_method not in {'CASH', 'GCASH'}:
        flash('Promo sales support Cash or GCash only.', 'error')
        return redirect(url_for('cashier_terminal'))

    cust_id = None
    cust_name = 'Walk-in Member'
    contact = 'N/A'
    points_earned = 0

    if reg_id:
        cust = Customer.query.get(reg_id)
        if cust:
            issue = customer_access_issue(cust)
            if issue:
                flash(issue, 'error')
                return redirect(url_for('cashier_terminal'))
            cust_id = cust.id
            cust_name = cust.name
            contact = cust.contact
            cust.accumulated_spend = (cust.accumulated_spend or 0.0) + promo.promo_price
            points_earned = int(promo.promo_price // 30)
            if points_earned > 0:
                cust.points_balance = (cust.points_balance or 0.0) + points_earned
                db.session.add(RewardLedger(
                    customer_id=cust.id,
                    points_change=points_earned,
                    reason=f"Promo Deal: {promo.title} (₱{promo.promo_price:,.2f})"
                ))

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
    )
    db.session.add(order)
    db.session.flush()

    db.session.add(OrderItem(
        order_id=order.id,
        product_id=None,
        product_name=f"[PROMO] {promo.title}",
        unit_price=promo.promo_price,
        cost_price=max(0.0, parse_float(promo.promo_cost, 0.0)),
        quantity=1,
        subtotal=promo.promo_price
    ))

    promo.claims_count = (promo.claims_count or 0) + 1
    promo.total_revenue = (promo.total_revenue or 0.0) + promo.promo_price
    if reg_id and cust_id:
        apply_member_marketing_rewards(cust, order)

    db.session.commit()
    flash(f"🎉 Promo Deal '{promo.title}' recorded ({dining_opt}) for {cust_name} (₱{promo.promo_price:,.2f})!", "success")
    return redirect(url_for('cashier_terminal'))

@app.route('/pos/create-reservation', methods=['POST'])
@require_cashier
def cashier_create_reservation():
    cust_type = request.form.get('customer_type', 'REGISTERED')
    reg_id = request.form.get('registered_customer_id')
    product_id = parse_int(request.form.get('product_id'), 0)
    qty = parse_int(request.form.get('quantity'), 1)
    dining_opt = request.form.get('dining_option', 'TAKEOUT').upper()
    target_time = request.form.get('target_time', '').strip() or 'Today'
    pay_method = request.form.get('payment_method', 'CASH').upper()
    notes = request.form.get('notes', '').strip() or 'In-Store Reservation'

    try:
        lines = validate_and_lock_cart([{'product_id': product_id, 'quantity': qty, 'options': request.form.get('selected_options', '')}], require_available=True)
        line = lines[0]
        prod = line['product']
        subtotal = line['subtotal']

        cust = None
        cust_name = 'Walk-in Guest'
        contact = 'N/A'
        if cust_type == 'REGISTERED':
            cust = db.session.get(Customer, parse_int(reg_id, 0))
            if not cust:
                raise OrderValidationError('Please select a registered member.')
            issue = customer_access_issue(cust)
            if issue:
                raise OrderValidationError(issue)
            cust_name = cust.name
            contact = cust.contact
        else:
            cust_name = request.form.get('custom_customer_name', '').strip() or 'Walk-in Reservation'
            contact = request.form.get('custom_contact', '').strip() or 'N/A'

        order = Order(
            order_type='RESERVATION',
            dining_option=dining_opt if dining_opt in {'DINE-IN', 'TAKEOUT'} else 'TAKEOUT',
            customer_id=cust.id if cust else None,
            customer_name=f'{cust_name} (Reserved: {target_time})',
            contact_number=contact,
            pickup_time=target_time,
            target_time=target_time,
            subtotal=subtotal,
            delivery_fee=0.0,
            total_amount=subtotal,
            payment_method=pay_method if pay_method in {'CASH', 'GCASH'} else 'CASH',
            payment_verified=False,
            status='VERIFICATION',
            notes=f'[{dining_opt} - RESERVED for {target_time}] {notes}',
        )
        db.session.add(order)
        db.session.flush()
        db.session.add(OrderItem(
            order_id=order.id,
            product_id=prod.id,
            product_name=prod.name,
            unit_price=line['unit_price'],
            cost_price=line['cost_price'],
            quantity=qty,
            subtotal=subtotal,
            selected_options=line.get('selected_options_json'),
        ))
        reserve_cart_stock(lines)
        db.session.commit()
        flash(f'📌 Reserved {prod.name} x{qty} ({dining_opt}) for {cust_name} (Pickup: {target_time}) — ₱{subtotal:,.2f}', 'success')
    except OrderValidationError as exc:
        db.session.rollback()
        flash(str(exc), 'error')
    except Exception:
        db.session.rollback()
        app.logger.exception('Cashier reservation failed')
        flash('Reservation failed due to a server error. Nothing was recorded.', 'error')
    return redirect(url_for('cashier_terminal'))

@app.route('/pos/misc-sale', methods=['POST'])
@require_cashier
def cashier_misc_sale():
    service_name = request.form.get('service_name', '').strip() or 'Printing / Custom Service'
    amount = parse_float(request.form.get('amount'), 0.0)
    pay_method = request.form.get('payment_method', 'CASH').upper()
    notes = request.form.get('notes', '').strip() or 'Over-the-counter Misc Service'
    reg_cust_id = request.form.get('registered_customer_id')
    custom_name = request.form.get('custom_customer_name', '').strip()

    if amount <= 0:
        flash("Amount must be greater than zero.", "error")
        return redirect(url_for('cashier_terminal'))
    if pay_method not in {'CASH', 'GCASH'}:
        flash('Misc sales support Cash or GCash only.', 'error')
        return redirect(url_for('cashier_terminal'))

    cust_id = None
    customer_name = 'Walk-in Customer'
    contact = 'N/A'

    if reg_cust_id:
        cust = Customer.query.get(reg_cust_id)
        if cust:
            issue = customer_access_issue(cust)
            if issue:
                flash(issue, 'error')
                return redirect(url_for('cashier_terminal'))
            cust_id = cust.id
            customer_name = cust.name
            contact = cust.contact
            cust.accumulated_spend = (cust.accumulated_spend or 0.0) + amount
            earned = int(amount // 30)
            if earned > 0:
                cust.points_balance = (cust.points_balance or 0.0) + earned
                db.session.add(RewardLedger(customer_id=cust.id, points_change=earned, reason=f"Service Purchase: {service_name}"))
    elif custom_name:
        customer_name = custom_name

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
    )
    db.session.add(order)
    db.session.flush()

    db.session.add(OrderItem(
        order_id=order.id,
        product_id=None,
        product_name=f"[Service] {service_name}",
        unit_price=amount,
        cost_price=0.0,
        quantity=1,
        subtotal=amount
    ))
    if reg_cust_id and cust_id:
        apply_member_marketing_rewards(cust, order)

    db.session.commit()
    flash(f"Misc Sale recorded: {service_name} for {customer_name} (₱{amount:,.2f})", "success")
    return redirect(url_for('cashier_terminal'))

@app.route('/pos/record-change-fund', methods=['POST'])
@require_cashier
def cashier_record_change_fund():
    title = request.form.get('fund_title', 'Opening Petty/Change Fund').strip()
    amount = parse_float(request.form.get('amount'), 0.0)
    notes = request.form.get('notes', 'Ulam / Register Drawer Starting Cash').strip()
    staff_user = session.get('cashier_user') or session.get('admin_user') or 'Cashier'

    if amount <= 0:
        flash("Change fund amount must be greater than zero.", "error")
        return redirect(url_for('cashier_terminal'))

    db.session.add(ChangeFund(fund_title=title, amount=amount, notes=notes, created_by=staff_user))
    db.session.commit()
    flash(f"Change Fund (₱{amount:,.2f}) added to register drawer notes.", "success")
    return redirect(url_for('cashier_terminal'))

@app.route('/pos/create-collection', methods=['POST'])
@require_cashier
def cashier_create_collection():
    cust_type = request.form.get('customer_type', 'REGISTERED')
    item_choice_type = request.form.get('item_choice_type', 'PRODUCT')
    product_id = parse_int(request.form.get('product_id'), 0)
    qty = parse_int(request.form.get('quantity'), 1)
    dining_opt = request.form.get('dining_option', 'TAKEOUT').upper()
    notes = request.form.get('notes', '').strip()

    try:
        lines = None
        prod = None
        if item_choice_type == 'PRODUCT':
            lines = validate_and_lock_cart([{'product_id': product_id, 'quantity': qty, 'options': request.form.get('selected_options', '')}], require_available=True)
            line = lines[0]
            prod = line['product']
            prod_name = prod.name
            unit_p = line['unit_price']
            cost_p = line['cost_price']
            amount = line['subtotal']
        else:
            if qty < 1:
                raise OrderValidationError('Quantity must be at least 1.')
            prod_name = request.form.get('custom_title', '').strip() or 'Custom Receivable Service'
            unit_p = parse_float(request.form.get('custom_amount'), 0.0)
            cost_p = 0.0
            amount = unit_p * qty
            if amount <= 0:
                raise OrderValidationError('Amount must be greater than zero.')

        cust = None
        cust_name = 'Walk-in Customer'
        contact = 'N/A'
        if cust_type == 'REGISTERED':
            cust = db.session.get(Customer, parse_int(request.form.get('registered_customer_id'), 0))
            if not cust:
                raise OrderValidationError('Please select a registered member.')
            issue = customer_access_issue(cust)
            if issue:
                raise OrderValidationError(issue)
            if not cust.is_credit_eligible:
                raise OrderValidationError('This member is not authorized for A/R credit.')
            available = customer_available_credit(cust, include_pending=True)
            if amount > available + 1e-9:
                raise OrderValidationError(f'Credit limit exceeded. Available credit: ₱{available:,.2f}.')
            cust_name = cust.name
            contact = cust.contact
            cust.outstanding_ar = (cust.outstanding_ar or 0.0) + amount
        else:
            cust_name = request.form.get('custom_customer_name', '').strip() or 'Custom Account'
            contact = request.form.get('custom_contact', '').strip() or 'N/A'

        order = Order(
            order_type='COLLECTION',
            dining_option=dining_opt if dining_opt in {'DINE-IN', 'TAKEOUT'} else 'TAKEOUT',
            customer_id=cust.id if cust else None,
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
            notes=f'[{dining_opt}] Attributable Item: {prod_name} (x{qty})',
        )
        db.session.add(order)
        db.session.flush()
        db.session.add(OrderItem(
            order_id=order.id,
            product_id=prod.id if prod else None,
            product_name=prod_name,
            unit_price=unit_p,
            cost_price=cost_p,
            quantity=qty,
            subtotal=amount,
            selected_options=line.get('selected_options_json') if lines else None,
        ))
        if lines:
            reserve_cart_stock(lines)
        db.session.commit()
        flash(f'For Collection ({dining_opt}) recorded for {cust_name}: {prod_name} x{qty} (₱{amount:,.2f})', 'info')
    except OrderValidationError as exc:
        db.session.rollback()
        flash(str(exc), 'error')
    except Exception:
        db.session.rollback()
        app.logger.exception('For Collection entry failed')
        flash('For Collection entry failed due to a server error.', 'error')
    return redirect(url_for('cashier_terminal'))

@app.route('/pos/settle-collection/<int:order_id>', methods=['POST'])
@require_cashier
def cashier_settle_collection(order_id):
    order = Order.query.get_or_404(order_id)
    pay_method = request.form.get('payment_method', 'CASH').upper()
    if pay_method not in {'CASH', 'GCASH'}:
        flash('Settlement payment must be Cash or GCash.', 'error')
        return redirect(url_for('cashier_terminal'))
    if not order.is_unpaid:
        flash(f'Order #{order.id} has already been settled.', 'info')
        return redirect(url_for('cashier_terminal'))
    
    order.is_unpaid = False
    order.status = 'COMPLETED'
    order.payment_method = pay_method
    order.payment_verified = True

    is_same_day = (utc_naive_to_ph(order.created_at).date() == ph_today())
    earned = 0

    if order.customer_id:
        cust = Customer.query.get(order.customer_id)
        if cust:
            cust.outstanding_ar = max(0.0, (cust.outstanding_ar or 0.0) - order.total_amount)
            cust.accumulated_spend = (cust.accumulated_spend or 0.0) + order.total_amount
            
            if is_same_day:
                earned = int(order.total_amount // 30)
                if earned > 0:
                    cust.points_balance = (cust.points_balance or 0.0) + earned
                    db.session.add(RewardLedger(customer_id=cust.id, points_change=earned, reason=f"Same-Day Settled Credit #{order.id}"))
            # Referral and scheduled campaign rewards are tied to the original purchase,
            # so they can be released once the credit order is actually paid.
            apply_member_marketing_rewards(cust, order)

    db.session.commit()
    bonus_msg = f" (+{earned} pts earned for Same-Day payment!)" if earned > 0 else " (No points: paid after order date)"
    flash(f"Collection #{order.id} for {order.customer_name} settled via {pay_method}!{bonus_msg}", "success")
    return redirect(url_for('cashier_terminal'))

@app.route('/pos/settle-customer-credit/<int:cust_id>', methods=['POST'])
@require_cashier
def cashier_settle_customer_credit(cust_id):
    cust = Customer.query.get_or_404(cust_id)
    amount = parse_float(request.form.get('amount'), cust.outstanding_ar or 0.0)
    pay_method = request.form.get('payment_method', 'CASH').upper()

    if pay_method not in {'CASH', 'GCASH'}:
        flash('Credit settlement payment must be Cash or GCash.', 'error')
        return redirect(url_for('cashier_terminal'))
    if (cust.outstanding_ar or 0.0) <= 0:
        flash(f'{cust.name} has no outstanding credit balance.', 'info')
        return redirect(url_for('cashier_terminal'))
    if amount <= 0:
        flash("Amount must be greater than zero.", "error")
        return redirect(url_for('cashier_terminal'))

    amount_to_pay = min(amount, cust.outstanding_ar)
    cust.outstanding_ar = max(0.0, cust.outstanding_ar - amount_to_pay)
    cust.accumulated_spend = (cust.accumulated_spend or 0.0) + amount_to_pay

    db.session.commit()
    flash(f"Settled ₱{amount_to_pay:,.2f} credit balance for {cust.name} via {pay_method}!", "success")
    return redirect(url_for('cashier_terminal'))

@app.route('/pos/record-expense', methods=['POST'])
@require_cashier
def cashier_record_expense():
    title = request.form.get('title', '').strip()
    amount = parse_float(request.form.get('amount'), 0.0)
    category = request.form.get('category', 'Supplies')
    staff_user = session.get('cashier_user') or session.get('admin_user') or 'Cashier'

    if not title or amount <= 0:
        flash("Please provide a valid title and amount.", "error")
        return redirect(url_for('cashier_terminal'))

    db.session.add(Expense(title=title, amount=amount, category=category, created_by=staff_user))
    db.session.commit()
    flash(f"Expense recorded: {title} (₱{amount:,.2f})", "success")
    return redirect(url_for('cashier_terminal'))

@app.route('/pos/record-vault-drop', methods=['POST'])
@require_cashier
def cashier_record_vault_drop():
    drop_num = parse_int(request.form.get('drop_number'), 1)
    amount = parse_float(request.form.get('amount'), 0.0)
    notes = request.form.get('notes', '').strip()
    breakdown = request.form.get('cash_breakdown', '').strip()
    staff_user = session.get('cashier_user') or session.get('admin_user') or 'Cashier'

    if drop_num < 1:
        flash('Vault drop number must be at least 1.', 'error')
        return redirect(url_for('cashier_terminal'))
    if amount <= 0:
        flash("Drop amount must be greater than zero.", "error")
        return redirect(url_for('cashier_terminal'))

    db.session.add(VaultDrop(drop_number=drop_num, amount=amount, notes=notes, cash_breakdown=breakdown, created_by=staff_user))
    db.session.commit()
    flash(f"Vault Cash Drop #{drop_num} recorded: ₱{amount:,.2f}", "success")
    return redirect(url_for('cashier_terminal'))

def _apply_pending_order_total_delta(order, delta):
    """Apply a cashier adjustment without disturbing existing delivery/discount math."""
    delta = round(parse_float(delta, 0.0), 2)
    order.subtotal = max(0.0, round(parse_float(order.subtotal, 0.0) + delta, 2))
    order.total_amount = max(0.0, round(parse_float(order.total_amount, 0.0) + delta, 2))


def _append_order_adjustment_audit(order, message):
    stamp = ph_now().strftime('%Y-%m-%d %I:%M %p')
    staff_user = session.get('cashier_user') or session.get('admin_user') or 'Cashier'
    entry = f'[{stamp} PH] {staff_user}: {message}'
    existing = (order.collection_notes or '').strip()
    order.collection_notes = (existing + (' | ' if existing else '') + entry)[-250:]


@app.route('/pos/adjust-order/<int:order_id>', methods=['POST'])
@require_cashier
def cashier_adjust_pending_order(order_id):
    """Add/remove cashier-approved extra charges before a queued order is accepted.

    This is intentionally restricted to VERIFICATION orders. Original product lines
    cannot be deleted here; only lines created by this adjustment route can be removed.
    """
    order = Order.query.get_or_404(order_id)
    if order.status != 'VERIFICATION':
        flash(f'Order #{order.id} can no longer be adjusted because it is {order.status}.', 'error')
        return redirect(url_for('cashier_terminal'))

    action = str(request.form.get('action', 'ADD_CHARGE')).upper()
    try:
        if action == 'ADD_CHARGE':
            description = re.sub(r'\s+', ' ', str(request.form.get('description', '')).strip())[:100]
            qty = parse_int(request.form.get('quantity'), 1)
            unit_fee = round(parse_float(request.form.get('unit_fee'), 0.0), 2)

            if not description:
                raise OrderValidationError('Please describe the additional item or service.')
            if qty < 1 or qty > 99:
                raise OrderValidationError('Additional charge quantity must be between 1 and 99.')
            if unit_fee <= 0 or unit_fee > 100000:
                raise OrderValidationError('Additional fee must be greater than ₱0.00.')

            line_total = round(unit_fee * qty, 2)
            item = OrderItem(
                order_id=order.id,
                product_id=None,
                product_name=f'[Cashier Add-on] {description}',
                unit_price=unit_fee,
                cost_price=0.0,
                quantity=qty,
                subtotal=line_total,
                selected_options=None,
            )
            db.session.add(item)
            db.session.flush()
            _apply_pending_order_total_delta(order, line_total)

            cash_received_raw = str(request.form.get('cash_received', '')).strip()
            if order.payment_method == 'CASH' and cash_received_raw:
                cash_received = round(parse_float(cash_received_raw, -1), 2)
                if cash_received < 0:
                    raise OrderValidationError('Cash received/change-for amount is invalid.')
                order.change_for = cash_received or None

            _append_order_adjustment_audit(
                order,
                f'Added {description} x{qty} @ ₱{unit_fee:,.2f} (+₱{line_total:,.2f}). New total ₱{order.total_amount:,.2f}.'
            )
            db.session.commit()
            extra = ''
            if order.payment_method == 'GCASH':
                extra = ' Confirm the additional GCash/payment amount before accepting.'
            elif order.payment_method == 'CASH' and order.change_for and order.change_for + 1e-9 < order.total_amount:
                extra = ' Cash received/change-for is below the new total; update it before accepting.'
            flash(f'Order #{order.id} updated: +₱{line_total:,.2f}. New total ₱{order.total_amount:,.2f}.{extra}', 'success')

        elif action == 'REMOVE_LINE':
            item_id = parse_int(request.form.get('item_id'), 0)
            item = db.session.get(OrderItem, item_id)
            if not item or item.order_id != order.id:
                raise OrderValidationError('Adjustment line was not found.')
            if item.product_id is not None or not str(item.product_name or '').startswith('[Cashier Add-on] '):
                raise OrderValidationError('Only cashier-added charge lines can be removed here.')

            removed_total = parse_float(item.subtotal, 0.0)
            removed_name = str(item.product_name).replace('[Cashier Add-on] ', '', 1)
            db.session.delete(item)
            _apply_pending_order_total_delta(order, -removed_total)
            _append_order_adjustment_audit(
                order,
                f'Removed cashier add-on {removed_name} (-₱{removed_total:,.2f}). New total ₱{order.total_amount:,.2f}.'
            )
            db.session.commit()
            flash(f'Cashier add-on removed from Order #{order.id}. New total ₱{order.total_amount:,.2f}.', 'info')

        elif action == 'UPDATE_CASH':
            if order.payment_method != 'CASH':
                raise OrderValidationError('Cash received can only be updated for CASH orders.')
            cash_received = round(parse_float(request.form.get('cash_received'), -1), 2)
            if cash_received < order.total_amount:
                raise OrderValidationError(f'Cash received cannot be below the order total of ₱{order.total_amount:,.2f}.')
            order.change_for = cash_received
            _append_order_adjustment_audit(order, f'Updated cash received/change-for to ₱{cash_received:,.2f}.')
            db.session.commit()
            flash(f'Cash received for Order #{order.id} updated to ₱{cash_received:,.2f}.', 'success')
        else:
            raise OrderValidationError('Invalid order adjustment action.')

    except OrderValidationError as exc:
        db.session.rollback()
        flash(str(exc), 'error')
    except Exception:
        db.session.rollback()
        app.logger.exception('Failed to adjust pending Order #%s', order_id)
        flash('Unable to adjust this order. Please check the server log.', 'error')

    return redirect(url_for('cashier_terminal'))


@app.route('/pos/verify/<int:order_id>', methods=['POST'])
@require_cashier
def verify_order(order_id):
    order = Order.query.get_or_404(order_id)
    action = request.form.get('action')

    if order.status != 'VERIFICATION':
        flash(f'Order #{order.id} is already {order.status}.', 'info')
        return redirect(url_for('cashier_terminal'))

    if action == 'ACCEPT':
        if order.payment_method == 'CASH' and order.change_for and order.change_for + 1e-9 < order.total_amount:
            flash(
                f'Order #{order.id} total is ₱{order.total_amount:,.2f}, but cash received/change-for is only ₱{order.change_for:,.2f}. '
                'Use Adjust to update the cash amount before accepting.',
                'error'
            )
            return redirect(url_for('cashier_terminal'))

        if order.payment_method == 'CREDIT':
            if not order.customer_id:
                flash('Credit order has no registered customer and cannot be accepted.', 'error')
                return redirect(url_for('cashier_terminal'))
            cust = db.session.get(Customer, order.customer_id)
            issue = customer_access_issue(cust)
            if issue:
                flash(issue, 'error')
                return redirect(url_for('cashier_terminal'))
            if not cust.is_credit_eligible:
                flash('Customer is no longer authorized for credit.', 'error')
                return redirect(url_for('cashier_terminal'))
            available = max(0.0, parse_float(cust.credit_limit, 0.0) - parse_float(cust.outstanding_ar, 0.0))
            if order.total_amount > available + 1e-9:
                flash(f'Credit limit exceeded. Available credit is ₱{available:,.2f}.', 'error')
                return redirect(url_for('cashier_terminal'))
            cust.outstanding_ar = (cust.outstanding_ar or 0.0) + order.total_amount
            order.is_unpaid = True
            order.payment_verified = False
            order.status = 'COMPLETED'
        else:
            order.payment_verified = True
            order.status = 'COMPLETED'
            if order.customer_id:
                cust = db.session.get(Customer, order.customer_id)
                if cust and not customer_access_issue(cust):
                    cust.accumulated_spend = (cust.accumulated_spend or 0.0) + order.total_amount
                    earned = int(order.total_amount // 30)
                    if earned > 0:
                        cust.points_balance = (cust.points_balance or 0.0) + earned
                        db.session.add(RewardLedger(
                            customer_id=cust.id,
                            points_change=earned,
                            reason=f'Purchase Order #{order.id}',
                        ))
                    apply_member_marketing_rewards(cust, order)
        db.session.commit()
        if order.payment_method == 'CREDIT':
            flash(f'Order #{order.id} accepted as A/R Credit and added to Member Credit AR.', 'success')
        else:
            flash(f'Order #{order.id} accepted and completed. Details ready to print!', 'success')
    elif action == 'REJECT':
        for item in order.items:
            if item.product_id:
                prod = db.session.get(Product, item.product_id)
                if prod:
                    prod.stock = parse_int(prod.stock, 0) + item.quantity
        order.status = 'CANCELLED'
        db.session.commit()
        flash(f'Order #{order.id} cancelled and reserved stock restored.', 'info')
    else:
        flash('Invalid verification action.', 'error')

    return redirect(url_for('cashier_terminal'))

@app.route('/admin/settings/hours', methods=['POST'])
@require_cashier
def update_operating_hours():
    """Update store/delivery operating hours from the cashier settings modal."""
    time_fields = (
        'store_open_time',
        'store_close_time',
        'delivery_open_time',
        'delivery_close_time',
    )

    values = {}
    for key in time_fields:
        value = request.form.get(key, '').strip()
        try:
            datetime.strptime(value, '%H:%M')
        except (TypeError, ValueError):
            flash(f"Invalid time value for {key.replace('_', ' ')}.", "error")
            return redirect(url_for('cashier_terminal'))
        values[key] = value

    values['is_store_open'] = 'true' if request.form.get('is_store_open') else 'false'
    values['is_delivery_enabled'] = 'true' if request.form.get('is_delivery_enabled') else 'false'

    try:
        for key, value in values.items():
            setting = StoreSetting.query.filter_by(key=key).first()
            if setting:
                setting.value = value
            else:
                db.session.add(StoreSetting(key=key, value=value))
        db.session.commit()
        flash("Operating schedule updated.", "success")
    except Exception:
        db.session.rollback()
        app.logger.exception('Could not save operating schedule')
        flash("Could not save the operating schedule.", "error")

    if session.get('cashier_user'):
        return redirect(url_for('cashier_terminal'))
    return redirect(url_for('admin_dashboard'))

# ==================== MASTER ADMIN, CONTROLS & SETTINGS ====================

@app.route('/admin')
@require_admin
def admin_dashboard():
    sort_by = request.args.get('sort', 'likes_desc')

    query = Product.query
    if sort_by == 'likes_desc': query = query.order_by(Product.total_likes.desc())
    elif sort_by == 'price_asc': query = query.order_by(Product.price.asc())
    elif sort_by == 'price_desc': query = query.order_by(Product.price.desc())
    elif sort_by == 'name_asc': query = query.order_by(Product.name.asc())
    elif sort_by == 'category': query = query.order_by(Product.category_name.asc(), Product.name.asc())
    elif sort_by == 'featured': query = query.order_by(Product.is_featured.desc(), Product.name.asc())
    elif sort_by == 'top_seller': query = query.order_by(Product.is_top_seller.desc(), Product.name.asc())

    products = query.all()
    categories = Category.query.all()
    staff_members = Staff.query.all()
    customers = Customer.query.order_by(Customer.id.desc()).all()
    delivery_zones = DeliveryZone.query.all()
    all_orders = Order.query.order_by(Order.created_at.desc()).limit(150).all()
    all_expenses = Expense.query.order_by(Expense.created_at.desc()).all()
    vault_drops = VaultDrop.query.order_by(VaultDrop.created_at.desc()).all()
    promotions = PromotionTracker.query.order_by(PromotionTracker.created_at.desc()).all()

    try:
        unique_visitors = SiteVisitor.query.count()
        total_accumulated_visits = db.session.query(db.func.coalesce(db.func.sum(SiteVisitor.visit_count), 0)).scalar() or unique_visitors
    except Exception:
        app.logger.exception('Admin visitor metrics query failed')
        unique_visitors = 0
        total_accumulated_visits = 0

    today = ph_today()
    day_start, next_day = ph_day_utc_bounds(today)
    week_ago = utc_now() - timedelta(days=7)
    month_ago = utc_now() - timedelta(days=30)

    daily_orders = Order.query.filter(Order.created_at >= day_start, Order.created_at < next_day, Order.status == 'COMPLETED').all()
    weekly_orders = Order.query.filter(Order.created_at >= week_ago, Order.status == 'COMPLETED').all()
    monthly_orders = Order.query.filter(Order.created_at >= month_ago, Order.status == 'COMPLETED').all()
    all_completed = Order.query.filter_by(status='COMPLETED').all()

    daily_exp = db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0.0)).filter(Expense.created_at >= day_start, Expense.created_at < next_day).scalar() or 0.0
    weekly_exp = db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0.0)).filter(Expense.created_at >= week_ago).scalar() or 0.0
    monthly_exp = db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0.0)).filter(Expense.created_at >= month_ago).scalar() or 0.0
    total_exp_all = sum(e.amount for e in all_expenses)

    daily_vault = db.session.query(db.func.coalesce(db.func.sum(VaultDrop.amount), 0.0)).filter(VaultDrop.created_at >= day_start, VaultDrop.created_at < next_day).scalar() or 0.0
    weekly_vault = db.session.query(db.func.coalesce(db.func.sum(VaultDrop.amount), 0.0)).filter(VaultDrop.created_at >= week_ago).scalar() or 0.0
    monthly_vault = db.session.query(db.func.coalesce(db.func.sum(VaultDrop.amount), 0.0)).filter(VaultDrop.created_at >= month_ago).scalar() or 0.0
    all_vault = db.session.query(db.func.coalesce(db.func.sum(VaultDrop.amount), 0.0)).scalar() or 0.0

    def calc_period(orders, exp, vault_drop_sales):
        order_rev = sum(o.total_amount for o in orders)
        total_rev = order_rev + vault_drop_sales
        cost = sum(sum((getattr(it, 'cost_price', 0.0) or 0.0) * it.quantity for it in o.items) for o in orders)
        gross_p = total_rev - cost
        net_p = gross_p - exp
        return {
            'order_rev': order_rev,
            'vault_sales': vault_drop_sales,
            'rev': total_rev,
            'cost': cost,
            'gross_p': gross_p,
            'exp': exp,
            'net_p': net_p
        }

    fin_daily = calc_period(daily_orders, daily_exp, daily_vault)
    fin_weekly = calc_period(weekly_orders, weekly_exp, weekly_vault)
    fin_monthly = calc_period(monthly_orders, monthly_exp, monthly_vault)
    fin_all = calc_period(all_completed, total_exp_all, all_vault)

    product_sales_stats = {}
    food_revenue_total = 0.0
    service_revenue_total = 0.0

    for o in all_completed:
        for it in o.items:
            pname = it.product_name
            if pname not in product_sales_stats:
                product_sales_stats[pname] = {'qty': 0, 'revenue': 0.0, 'cost': 0.0}
            product_sales_stats[pname]['qty'] += (it.quantity or 0)
            product_sales_stats[pname]['revenue'] += (it.subtotal or 0.0)
            product_sales_stats[pname]['cost'] += (getattr(it, 'cost_price', 0.0) or 0.0) * (it.quantity or 0)

            if '[Service]' in pname or o.order_type == 'SERVICE/MISC' or 'Printing' in pname:
                service_revenue_total += (it.subtotal or 0.0)
            else:
                food_revenue_total += (it.subtotal or 0.0)

    food_revenue_total += all_vault
    total_ar = sum((c.outstanding_ar or 0.0) for c in customers)

    bonus_campaigns = BonusCampaign.query.order_by(BonusCampaign.created_at.desc()).all()
    product_suggestions = ProductSuggestion.query.order_by(ProductSuggestion.created_at.desc()).all()

    # Group near-identical requests (case/punctuation-insensitive) so repeated demand is obvious.
    demand_map = {}
    suggestion_repeat_counts = {}
    for suggestion in product_suggestions:
        normalized = re.sub(r'[^a-z0-9]+', ' ', (suggestion.suggestion_text or '').lower()).strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        key = normalized or f'__suggestion_{suggestion.id}'
        bucket = demand_map.setdefault(key, {
            'label': suggestion.suggestion_text.strip(),
            'count': 0,
        })
        bucket['count'] += 1

    for suggestion in product_suggestions:
        normalized = re.sub(r'[^a-z0-9]+', ' ', (suggestion.suggestion_text or '').lower()).strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        key = normalized or f'__suggestion_{suggestion.id}'
        suggestion_repeat_counts[suggestion.id] = demand_map[key]['count']

    suggestion_demand = sorted(
        demand_map.values(),
        key=lambda row: (-row['count'], row['label'].lower())
    )[:10]

    seven_days_ago = utc_now() - timedelta(days=7)
    marketing_metrics = {
        'qr_scans_7d': PortalEvent.query.filter(PortalEvent.event_type == 'QR_SCAN', PortalEvent.created_at >= seven_days_ago).count(),
        'portal_logins_7d': PortalEvent.query.filter(PortalEvent.event_type == 'LOGIN', PortalEvent.created_at >= seven_days_ago).count(),
        'registrations_7d': PortalEvent.query.filter(PortalEvent.event_type == 'REGISTER', PortalEvent.created_at >= seven_days_ago).count(),
        'counter_registrations_7d': PortalEvent.query.filter(PortalEvent.event_type == 'REGISTER', PortalEvent.source == 'counter', PortalEvent.created_at >= seven_days_ago).count(),
        'suggestions_7d': ProductSuggestion.query.filter(ProductSuggestion.created_at >= seven_days_ago).count(),
        'suggestions_total': ProductSuggestion.query.count(),
        'suggestions_open': ProductSuggestion.query.filter(ProductSuggestion.status != 'ARCHIVED').count(),
        'referral_rewards': ReferralReward.query.count(),
    }

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
                           current_sort=sort_by,
                           bonus_campaigns=bonus_campaigns,
                           marketing_metrics=marketing_metrics,
                           product_suggestions=product_suggestions,
                           suggestion_repeat_counts=suggestion_repeat_counts,
                           suggestion_demand=suggestion_demand,
                           suggestion_statuses=SUGGESTION_STATUSES)

@app.route('/admin/product-suggestion/<int:suggestion_id>/status', methods=['POST'])
@require_admin
def admin_update_product_suggestion_status(suggestion_id):
    suggestion = ProductSuggestion.query.get_or_404(suggestion_id)
    new_status = request.form.get('status', 'NEW').strip().upper()
    if new_status not in SUGGESTION_STATUSES:
        flash('Invalid suggestion status.', 'error')
        return redirect(url_for('admin_dashboard') + '#customerSuggestions')

    suggestion.status = new_status
    db.session.commit()
    flash(f"Suggestion #{suggestion.id} marked {new_status}.", 'success')
    return redirect(url_for('admin_dashboard') + '#customerSuggestions')

@app.route('/admin/allocate-vault-drop/<int:drop_id>', methods=['POST'])
@require_admin
def admin_allocate_vault_drop(drop_id):
    drop = VaultDrop.query.get_or_404(drop_id)
    cust_id = request.form.get('customer_id')
    product_id = request.form.get('product_id')
    allocated_amount = parse_float(request.form.get('amount'), 0.0)
    qty = parse_int(request.form.get('quantity'), 1)

    if allocated_amount <= 0 or allocated_amount > drop.amount:
        flash("Allocated amount must be between ₱0.01 and the remaining drop balance.", "error")
        return redirect(url_for('admin_dashboard'))

    cust = Customer.query.get(int(cust_id)) if cust_id else None
    prod = Product.query.get(int(product_id)) if product_id else None
    if cust:
        issue = customer_access_issue(cust)
        if issue:
            flash(issue, 'error')
            return redirect(url_for('admin_dashboard'))
    if qty < 1:
        flash('Quantity must be at least 1.', 'error')
        return redirect(url_for('admin_dashboard'))

    drop.amount = max(0.0, drop.amount - allocated_amount)

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
    )
    db.session.add(order)
    db.session.flush()

    db.session.add(OrderItem(
        order_id=order.id,
        product_id=prod.id if prod else None,
        product_name=prod.name if prod else f"Ulam Sale (Drop #{drop.drop_number})",
        unit_price=allocated_amount / qty,
        cost_price=max(0.0, parse_float(prod.cost, 0.0)) if prod else 0.0,
        quantity=qty,
        subtotal=allocated_amount
    ))

    if cust:
        cust.accumulated_spend = (cust.accumulated_spend or 0.0) + allocated_amount
        earned = int(allocated_amount // 30)
        if earned > 0:
            cust.points_balance = (cust.points_balance or 0.0) + earned
            db.session.add(RewardLedger(
                customer_id=cust.id,
                points_change=earned,
                reason=f"Allocated Sale from Drop #{drop.drop_number}"
            ))
        apply_member_marketing_rewards(cust, order)

    db.session.commit()
    flash(f"Allocated ₱{allocated_amount:,.2f} from Drop #{drop.drop_number} into a dedicated Order #{order.id}!", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reassign-order/<int:order_id>', methods=['POST'])
@require_admin
def admin_reassign_order(order_id):
    order = Order.query.get_or_404(order_id)
    new_cust_id = request.form.get('customer_id')

    if not new_cust_id:
        flash("Please select a target customer.", "error")
        return redirect(url_for('admin_dashboard'))

    new_cust = Customer.query.get_or_404(int(new_cust_id))
    issue = customer_access_issue(new_cust)
    if issue:
        flash(issue, 'error')
        return redirect(url_for('admin_dashboard'))
    old_cust = Customer.query.get(order.customer_id) if order.customer_id else None

    if old_cust and order.status == 'COMPLETED' and order.payment_verified:
        earned = int(order.total_amount // 30)
        old_cust.points_balance = max(0.0, (old_cust.points_balance or 0.0) - earned)
        old_cust.accumulated_spend = max(0.0, (old_cust.accumulated_spend or 0.0) - order.total_amount)
        reverse_member_marketing_rewards_for_order(order)

    order.customer_id = new_cust.id
    order.customer_name = new_cust.name
    order.contact_number = new_cust.contact

    if order.status == 'COMPLETED' and order.payment_verified:
        earned_new = int(order.total_amount // 30)
        new_cust.accumulated_spend = (new_cust.accumulated_spend or 0.0) + order.total_amount
        if earned_new > 0:
            new_cust.points_balance = (new_cust.points_balance or 0.0) + earned_new
            db.session.add(RewardLedger(
                customer_id=new_cust.id,
                points_change=earned_new,
                reason=f"Admin Reassigned Order #{order.id}"
            ))
        apply_member_marketing_rewards(new_cust, order)

    db.session.commit()
    flash(f"Transaction #{order.id} reassigned to '{new_cust.name}'.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update-expense/<int:expense_id>', methods=['POST'])
@require_admin
def admin_update_expense(expense_id):
    exp = Expense.query.get_or_404(expense_id)
    new_title = request.form.get('title', exp.title).strip()
    new_amount = parse_float(request.form.get('amount'), exp.amount or 0.0)
    new_category = request.form.get('category', exp.category).strip()
    if not new_title or new_amount <= 0:
        flash('Expense title and amount must be valid.', 'error')
        return redirect(url_for('admin_dashboard'))
    exp.title = new_title
    exp.amount = new_amount
    exp.category = new_category
    db.session.commit()
    flash(f"Expense #{exp.id} updated successfully.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete-expense/<int:expense_id>', methods=['POST'])
@require_admin
def admin_delete_expense(expense_id):
    exp = Expense.query.get_or_404(expense_id)
    db.session.delete(exp)
    db.session.commit()
    flash(f"Expense record removed.", "info")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete-product/<int:product_id>', methods=['POST'])
@require_admin
def admin_delete_product(product_id):
    prod = Product.query.get_or_404(product_id)
    prod_name = prod.name

    OrderItem.query.filter_by(product_id=prod.id).update({'product_id': None})
    ProductLike.query.filter_by(product_id=prod.id).delete()
    ProductComment.query.filter_by(product_id=prod.id).delete()

    db.session.delete(prod)
    db.session.commit()
    flash(f"Product '{prod_name}' permanently deleted.", "info")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/revert-order/<int:order_id>', methods=['POST'])
@require_admin
def admin_revert_order(order_id):
    order = Order.query.get_or_404(order_id)
    
    for item in order.items:
        if item.product_id:
            p = Product.query.get(item.product_id)
            if p:
                p.stock += item.quantity

    if order.customer_id and order.status == 'COMPLETED' and order.payment_verified:
        cust = Customer.query.get(order.customer_id)
        if cust:
            earned = int(order.total_amount // 30)
            cust.points_balance = max(0.0, (cust.points_balance or 0.0) - earned)
            cust.accumulated_spend = max(0.0, (cust.accumulated_spend or 0.0) - order.total_amount)
            if earned > 0:
                db.session.add(RewardLedger(
                    customer_id=cust.id,
                    points_change=-earned,
                    reason=f"Admin Reverted Sale #{order.id}"
                ))
        reverse_member_marketing_rewards_for_order(order)

    if order.is_unpaid and order.customer_id:
        cust = Customer.query.get(order.customer_id)
        if cust:
            cust.outstanding_ar = max(0.0, (cust.outstanding_ar or 0.0) - order.total_amount)

    db.session.delete(order)
    db.session.commit()
    flash(f"Order #{order_id} deleted & reverted.", "info")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/purge-dummy-orders/<int:cust_id>', methods=['POST'])
@require_admin
def admin_purge_dummy_orders(cust_id):
    cust = Customer.query.get_or_404(cust_id)
    dummy_orders = Order.query.filter_by(customer_id=cust.id).all()
    for o in dummy_orders:
        db.session.delete(o)
    cust.points_balance = 0.0
    cust.accumulated_spend = 0.0
    cust.outstanding_ar = 0.0
    RewardLedger.query.filter_by(customer_id=cust.id).delete()
    db.session.commit()
    flash(f"Purged test orders & reset points for '{cust.name}'.", "info")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete-customer/<int:cust_id>', methods=['POST'])
@require_admin
def admin_delete_customer(cust_id):
    cust = Customer.query.get_or_404(cust_id)
    Order.query.filter_by(customer_id=cust.id).delete()
    RewardLedger.query.filter_by(customer_id=cust.id).delete()
    ProductLike.query.filter_by(customer_id=cust.id).delete()
    ProductComment.query.filter_by(customer_id=cust.id).delete()
    db.session.delete(cust)
    db.session.commit()
    flash(f"Account '{cust.name}' permanently removed.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update-logo', methods=['POST'])
@require_admin
def admin_update_logo():
    new_logo = request.form.get('logo_url', '').strip()
    if new_logo:
        setting = StoreSetting.query.filter_by(key='logo_url').first()
        if not setting:
            db.session.add(StoreSetting(key='logo_url', value=new_logo))
        else:
            setting.value = new_logo
        db.session.commit()
        flash("Company logo updated across all portals.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add-product', methods=['POST'])
@require_admin
def admin_add_product():
    name = request.form.get('name', '').strip()
    category_name = request.form.get('category_name', 'Meals').strip() or 'Meals'
    price = parse_float(request.form.get('price'), 0.0)
    cost = parse_float(request.form.get('cost'), 0.0)
    allow_custom_amount = bool(request.form.get('allow_custom_amount'))
    minimum_order_amount = parse_float(request.form.get('minimum_order_amount'), 0.0)
    option_schema_raw = request.form.get('option_schema', '').strip()
    stock = parse_int(request.form.get('stock'), 100)
    image_url = request.form.get('image_url', '').strip()
    start_t = request.form.get('available_start_time', '').strip() or None
    end_t = request.form.get('available_end_time', '').strip() or None
    is_featured = bool(request.form.get('is_featured'))
    is_top_seller = bool(request.form.get('is_top_seller'))

    if not name or price <= 0:
        flash('Please enter a valid product name and selling price.', 'error')
        return redirect(url_for('admin_dashboard'))
    if cost < 0 or stock < 0:
        flash('Cost and stock cannot be negative.', 'error')
        return redirect(url_for('admin_dashboard'))
    if allow_custom_amount:
        if minimum_order_amount <= 0:
            minimum_order_amount = price
        if minimum_order_amount > price:
            flash('Minimum order amount cannot be higher than the regular product price.', 'error')
            return redirect(url_for('admin_dashboard'))
    else:
        minimum_order_amount = None

    try:
        option_schema = normalize_product_option_schema(option_schema_raw)
    except OrderValidationError as exc:
        flash(str(exc), 'error')
        return redirect(url_for('admin_dashboard'))

    db.session.add(Product(
        name=name,
        category_name=category_name,
        price=price,
        cost=cost,
        allow_custom_amount=allow_custom_amount,
        minimum_order_amount=minimum_order_amount,
        option_schema=option_schema,
        stock=stock,
        image_url=image_url,
        available_start_time=start_t,
        available_end_time=end_t,
        is_featured=is_featured,
        is_top_seller=is_top_seller,
        is_active=True,
    ))
    db.session.commit()
    flash(f"Product '{name}' added successfully with cost tracking enabled!", 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/batch-update-products', methods=['POST'])
@require_admin
def admin_batch_update_products():
    try:
        for pid_raw in request.form.getlist('product_id'):
            pid = parse_int(pid_raw, 0)
            prod = db.session.get(Product, pid)
            if not prod:
                continue
            price = parse_float(request.form.get(f'price_{pid}'), prod.price)
            cost = parse_float(request.form.get(f'cost_{pid}'), prod.cost or 0.0)
            stock = parse_int(request.form.get(f'stock_{pid}'), prod.stock or 0)
            allow_custom_amount = (f'allow_custom_amount_{pid}' in request.form)
            minimum_order_amount = parse_float(request.form.get(f'minimum_order_amount_{pid}'), 0.0)
            option_schema = normalize_product_option_schema(request.form.get(f'option_schema_{pid}', '').strip())
            if price <= 0 or cost < 0 or stock < 0:
                raise OrderValidationError(f'Invalid price/cost/stock for {prod.name}.')
            if allow_custom_amount:
                if minimum_order_amount <= 0:
                    minimum_order_amount = price
                if minimum_order_amount > price:
                    raise OrderValidationError(f'Minimum order amount for {prod.name} cannot exceed its regular price.')
            else:
                minimum_order_amount = None
            prod.price = price
            prod.cost = cost
            prod.allow_custom_amount = allow_custom_amount
            prod.minimum_order_amount = minimum_order_amount
            prod.option_schema = option_schema
            prod.stock = stock
            prod.image_url = request.form.get(f'image_url_{pid}', '').strip()
            prod.available_start_time = request.form.get(f'available_start_time_{pid}', '').strip() or None
            prod.available_end_time = request.form.get(f'available_end_time_{pid}', '').strip() or None
            prod.is_active = (f'is_active_{pid}' in request.form)
            prod.is_featured = (f'is_featured_{pid}' in request.form)
            prod.is_top_seller = (f'is_top_seller_{pid}' in request.form)
        db.session.commit()
        flash('Bulk product catalog and product costs updated.', 'success')
    except OrderValidationError as exc:
        db.session.rollback()
        flash(str(exc), 'error')
    except Exception:
        db.session.rollback()
        app.logger.exception('Bulk product update failed')
        flash('Bulk product update failed due to a server error.', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/toggle-credit/<int:cust_id>', methods=['POST'])
@require_admin
def admin_toggle_credit(cust_id):
    cust = Customer.query.get_or_404(cust_id)
    action = request.form.get('action', 'SET_LIMIT').upper()
    if action == 'TOGGLE':
        cust.is_credit_eligible = not cust.is_credit_eligible
    limit = request.form.get('credit_limit')
    if limit not in (None, ''):
        parsed_limit = parse_float(limit, -1)
        if parsed_limit < 0:
            flash('Credit limit cannot be negative.', 'error')
            return redirect(url_for('admin_dashboard'))
        cust.credit_limit = parsed_limit
    db.session.commit()
    state = 'enabled' if cust.is_credit_eligible else 'disabled'
    flash(f'Credit for {cust.name} is {state}; limit ₱{(cust.credit_limit or 0.0):,.2f}.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delivery-zones', methods=['POST'])
@require_admin
def admin_manage_delivery_zones():
    action = request.form.get('action')
    if action == 'ADD':
        place = request.form.get('place_name')
        brgy = request.form.get('barangay')
        rate = float(request.form.get('rate') or 40.0)
        dist = request.form.get('distance')
        note = request.form.get('note')
        db.session.add(DeliveryZone(place_name=place, barangay=brgy, rate=rate, distance=dist, note=note))
    elif action == 'DELETE':
        zid = request.form.get('zone_id')
        zone = DeliveryZone.query.get(zid)
        if zone:
            db.session.delete(zone)
    db.session.commit()
    flash("Delivery zones updated.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/renew-customer-card/<int:cust_id>', methods=['POST'])
@require_admin
def admin_renew_customer_card(cust_id):
    cust = Customer.query.get_or_404(cust_id)
    cust.card_status = 'ACTIVE'
    cust.card_expires_at = ph_today() + timedelta(days=365)
    db.session.commit()
    flash(f"Rewards card for '{cust.name}' renewed for 1 year.", 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reset-customer-pin/<int:cust_id>', methods=['POST'])
@require_admin
def admin_reset_customer_pin(cust_id):
    cust = Customer.query.get_or_404(cust_id)
    new_pin = request.form.get('new_pin', '').strip()
    if not is_valid_customer_pin(new_pin):
        flash('Customer PIN must be exactly 4 digits.', 'error')
    else:
        cust.pin_hash = generate_password_hash(new_pin)
        db.session.commit()
        flash(f"PIN for customer '{cust.name}' was reset successfully.", 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reset-staff-pin/<int:staff_id>', methods=['POST'])
@require_admin
def admin_reset_staff_pin(staff_id):
    staff = Staff.query.get_or_404(staff_id)
    new_pin = request.form.get('new_pin', '').strip()
    if not new_pin.isdigit() or not (4 <= len(new_pin) <= 8):
        flash('Staff PIN must contain 4 to 8 digits.', 'error')
        return redirect(url_for('admin_dashboard'))
    staff.pin_hash = generate_password_hash(new_pin)
    db.session.commit()
    flash(f"PIN for staff account '{staff.username}' was changed.", 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update-promo-financials/<int:promo_id>', methods=['POST'])
@require_admin
def admin_update_promo_financials(promo_id):
    promo = PromotionTracker.query.get_or_404(promo_id)
    price = parse_float(request.form.get('promo_price'), promo.promo_price)
    cost = parse_float(request.form.get('promo_cost'), promo.promo_cost or 0.0)
    if price <= 0 or cost < 0:
        flash('Promo price must be positive and promo cost cannot be negative.', 'error')
        return redirect(url_for('admin_dashboard'))
    promo.promo_price = price
    promo.promo_cost = cost
    db.session.commit()
    flash(f"Financials for '{promo.title}' updated.", 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/toggle-promo/<int:promo_id>', methods=['POST'])
@require_admin
def admin_toggle_promo(promo_id):
    promo = PromotionTracker.query.get_or_404(promo_id)
    promo.is_active = not promo.is_active
    if promo.is_active:
        promo.created_at = utc_now()
    db.session.commit()
    flash(f"Campaign '{promo.title}' status updated.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/toggle-promo-visibility/<int:promo_id>', methods=['POST'])
@require_admin
def admin_toggle_promo_visibility(promo_id):
    promo = PromotionTracker.query.get_or_404(promo_id)
    promo.is_visible = not getattr(promo, 'is_visible', True)
    db.session.commit()
    flash(f"Promo '{promo.title}' visibility updated.", "info")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/marketing/bonus-campaign/create', methods=['POST'])
@require_admin
def admin_create_bonus_campaign():
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    bonus_points = parse_float(request.form.get('bonus_points'), 0.0)
    points_multiplier = parse_float(request.form.get('points_multiplier'), 1.0)
    min_spend = parse_float(request.form.get('min_spend'), 0.0)
    start_date_raw = request.form.get('start_date', '').strip()
    end_date_raw = request.form.get('end_date', '').strip()
    start_time = request.form.get('start_time', '').strip() or None
    end_time = request.form.get('end_time', '').strip() or None
    weekdays = ','.join(request.form.getlist('weekdays')) or None

    if not title or (bonus_points <= 0 and points_multiplier <= 1.0) or min_spend < 0 or points_multiplier < 1.0:
        flash('Campaign needs a title and either fixed bonus points or a points multiplier above 1×.', 'error')
        return redirect(url_for('admin_dashboard'))
    try:
        start_date = datetime.strptime(start_date_raw, '%Y-%m-%d').date() if start_date_raw else None
        end_date = datetime.strptime(end_date_raw, '%Y-%m-%d').date() if end_date_raw else None
        if start_date and end_date and end_date < start_date:
            raise ValueError('End date must not be before start date.')
        if start_time:
            datetime.strptime(start_time, '%H:%M')
        if end_time:
            datetime.strptime(end_time, '%H:%M')
    except ValueError as exc:
        flash(f'Invalid campaign schedule: {exc}', 'error')
        return redirect(url_for('admin_dashboard'))

    db.session.add(BonusCampaign(
        title=title,
        description=description,
        bonus_points=bonus_points,
        points_multiplier=points_multiplier,
        min_spend=min_spend,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
        weekdays=weekdays,
        is_active=True,
    ))
    db.session.commit()
    flash(f"Bonus campaign '{title}' created.", 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/marketing/bonus-campaign/<int:campaign_id>/toggle', methods=['POST'])
@require_admin
def admin_toggle_bonus_campaign(campaign_id):
    campaign = BonusCampaign.query.get_or_404(campaign_id)
    campaign.is_active = not campaign.is_active
    db.session.commit()
    flash(f"Bonus campaign '{campaign.title}' {'activated' if campaign.is_active else 'paused'}.", 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/marketing/bonus-campaign/<int:campaign_id>/delete', methods=['POST'])
@require_admin
def admin_delete_bonus_campaign(campaign_id):
    campaign = BonusCampaign.query.get_or_404(campaign_id)
    BonusCampaignClaim.query.filter_by(campaign_id=campaign.id).delete(synchronize_session=False)
    db.session.delete(campaign)
    db.session.commit()
    flash(f"Bonus campaign '{campaign.title}' deleted.", 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/marketing/promo/create', methods=['POST'])
@require_admin
def admin_create_member_promo():
    promo_code = re.sub(r'[^A-Z0-9_]+', '_', request.form.get('promo_code', '').strip().upper()).strip('_')
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    price = parse_float(request.form.get('promo_price'), 0.0)
    cost = parse_float(request.form.get('promo_cost'), 0.0)
    portal_only = request.form.get('portal_only') == 'on'
    if not promo_code or not title or price <= 0 or cost < 0:
        flash('Promo code, title, positive price, and valid cost are required.', 'error')
        return redirect(url_for('admin_dashboard'))
    if PromotionTracker.query.filter_by(promo_code=promo_code).first():
        flash('That promo code already exists.', 'error')
        return redirect(url_for('admin_dashboard'))
    db.session.add(PromotionTracker(
        promo_code=promo_code,
        title=title,
        description=description,
        promo_price=price,
        promo_cost=cost,
        is_active=True,
        is_visible=True,
        portal_only=portal_only,
    ))
    db.session.commit()
    flash(f"Promo '{title}' created and is live for its 3-day cycle.", 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/marketing/qr-kit')
@require_admin
def admin_qr_kit():
    qr_sources = [
        ('counter', 'Counter Registration', 'Scan to join rewards before or after a walk-in purchase.'),
        ('table', 'Table Product Suggestion', 'Scan while waiting and tell us what you would like Macleen\'s to offer.'),
        ('receipt', 'Receipt Rewards Check', 'Scan after purchase to check points and member benefits.'),
        ('facebook', 'Facebook / Social', 'Use this QR on printed social promotions and posters.'),
    ]
    return render_template('qr_kit.html', qr_sources=qr_sources)

@app.route('/marketing/qr/<string:source>.svg')
def marketing_qr_svg(source):
    allowed = {'counter', 'table', 'receipt', 'facebook'}
    if source not in allowed:
        return Response('Unknown QR source', status=404, mimetype='text/plain')
    target = url_for('portal_start', source=source, _external=True)
    image = qrcode.make(target, image_factory=qrcode.image.svg.SvgPathImage)
    buffer = io.BytesIO()
    image.save(buffer)
    return Response(buffer.getvalue(), mimetype='image/svg+xml', headers={'Cache-Control': 'no-store'})

# ==================== CUSTOMER PORTAL ====================

@app.route('/portal/start/<string:source>')
def portal_start(source):
    allowed = {'counter', 'table', 'receipt', 'facebook'}
    if source not in allowed:
        source = 'direct'
    session['portal_source'] = source
    track_portal_event('QR_SCAN', source=source, customer_id=session.get('customer_id'))
    db.session.commit()
    section = {'table': 'suggest', 'counter': 'rewards', 'receipt': 'rewards', 'facebook': 'deals'}.get(source, 'rewards')
    if session.get('customer_id'):
        return redirect(url_for('customer_dashboard') + f'#{section}')
    return redirect(url_for('customer_login', src=source, next=section))

@app.route('/portal/login', methods=['GET', 'POST'])
def customer_login():
    source = request.args.get('src', '').strip() or session.get('portal_source') or 'direct'
    next_section = request.args.get('next', '').strip()
    if source:
        session['portal_source'] = source[:30]
    if request.method == 'POST':
        contact = request.form.get('contact', '').strip()
        pin = request.form.get('pin', '').strip()
        next_section = request.form.get('next', '').strip() or next_section
        cust = Customer.query.filter_by(contact=contact).first()
        if cust and check_password_hash(cust.pin_hash, pin):
            issue = customer_access_issue(cust)
            if issue:
                if cust.card_expires_at and ph_today() > cust.card_expires_at and (cust.card_status or 'ACTIVE').upper() == 'ACTIVE':
                    cust.card_status = 'EXPIRED'
                    db.session.commit()
                flash(issue, 'error')
                return render_template('customer_login.html', source=source, next_section=next_section)

            portal_source = session.get('portal_source', source)
            session.clear()
            session['customer_id'] = cust.id
            session['portal_source'] = portal_source
            session.permanent = True
            today = ph_today()
            if cust.last_daily_login != today:
                yesterday = today - timedelta(days=1)
                cust.login_streak = (cust.login_streak or 0) + 1 if cust.last_daily_login == yesterday else 1
                cust.points_balance = (cust.points_balance or 0.0) + 0.5
                cust.last_daily_login = today
                db.session.add(RewardLedger(
                    customer_id=cust.id,
                    points_change=0.5,
                    reason=f'Daily Login Reward (Day {cust.login_streak})',
                ))
            cust.last_active_at = utc_now()
            track_portal_event('LOGIN', source=portal_source, customer_id=cust.id)
            db.session.commit()
            target = url_for('customer_dashboard')
            return redirect(target + (f'#{next_section}' if next_section else ''))
        flash('Invalid Contact or PIN.', 'error')
    return render_template('customer_login.html', source=source, next_section=next_section)

@app.route('/portal/register', methods=['GET', 'POST'])
def customer_register():
    ref_code = request.args.get('ref', '').strip()
    source = request.args.get('src', '').strip() or session.get('portal_source') or 'direct'
    next_section = request.args.get('next', '').strip()
    if source:
        session['portal_source'] = source[:30]
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        contact = request.form.get('contact', '').strip()
        messenger = request.form.get('fb_messenger', '').strip()
        pin = request.form.get('pin', '').strip()
        address = request.form.get('default_address', '').strip()
        landmark = request.form.get('default_landmark', '').strip()
        ref = request.form.get('referral_code', '').strip() or ref_code
        source = request.form.get('source', '').strip() or source
        next_section = request.form.get('next', '').strip() or next_section

        if not name or not contact:
            flash('Name and mobile number are required.', 'error')
            return redirect(url_for('customer_register', ref=ref_code or None, src=source, next=next_section or None))
        if not is_valid_customer_pin(pin):
            flash('Security PIN must be exactly 4 digits.', 'error')
            return redirect(url_for('customer_register', ref=ref_code or None, src=source, next=next_section or None))
        if Customer.query.filter_by(contact=contact).first():
            flash('Contact number already registered.', 'error')
            return redirect(url_for('customer_login', src=source, next=next_section or None))

        today = ph_today()
        try:
            new_cust = Customer(
                name=name,
                email=email,
                contact=contact,
                fb_messenger=messenger,
                default_address=address,
                default_landmark=landmark,
                points_balance=0.5,
                pin_hash=generate_password_hash(pin),
                card_number=None,
                card_status='ACTIVE',
                card_expires_at=today + timedelta(days=365),
                referred_by=ref if ref else None,
                last_daily_login=today,
                login_streak=1,
                last_active_at=utc_now(),
            )
            db.session.add(new_cust)
            db.session.flush()
            new_cust.card_number = generate_unique_card_number(new_cust.id)

            db.session.add(RewardLedger(
                customer_id=new_cust.id,
                points_change=0.5,
                reason='Welcome Login Bonus',
            ))
            # Referral rewards are intentionally held until the new member completes a paid purchase.
            # This prevents fake registrations and rewards both sides for an actual new customer.
            track_portal_event('REGISTER', source=source, customer_id=new_cust.id)
            db.session.commit()
            portal_source = source
            session.clear()
            session['customer_id'] = new_cust.id
            session['portal_source'] = portal_source
            session.permanent = True
            if ref:
                flash('🎉 Welcome! +0.5 point added. Complete your first paid purchase to unlock the referral bonus for both of you!', 'success')
            else:
                flash('🎉 Welcome! You earned 0.5 points!', 'success')
            target = url_for('customer_dashboard')
            return redirect(target + (f'#{next_section}' if next_section else ''))
        except Exception:
            db.session.rollback()
            app.logger.exception('Customer registration failed for contact=%s', contact)
            flash('Registration could not be completed. Please try again or ask staff for help.', 'error')
            return redirect(url_for('customer_register', ref=ref_code or None, src=source, next=next_section or None))

    return render_template('customer_register.html', ref_code=ref_code, source=source, next_section=next_section)

@app.route('/portal/dashboard')
def customer_dashboard():
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))

    cust = Customer.query.get(session['customer_id'])
    if not cust:
        session.pop('customer_id', None)
        flash('Account session expired. Please log in again.', 'info')
        return redirect(url_for('customer_login'))

    issue = customer_access_issue(cust)
    if issue:
        session.pop('customer_id', None)
        flash(issue, 'error')
        return redirect(url_for('customer_login'))

    if getattr(cust, 'login_streak', None) is None:
        cust.login_streak = 1
        db.session.commit()

    my_orders = Order.query.filter_by(customer_id=cust.id).order_by(Order.created_at.desc()).limit(30).all()
    active_promos = PromotionTracker.query.filter_by(is_active=True, is_visible=True).order_by(PromotionTracker.created_at.desc()).all()
    # Preserve the existing 3-day promo cycle automatically.
    active_promos = [p for p in active_promos if (utc_now() - p.created_at).days <= 3]
    bonus_campaigns = get_active_bonus_campaigns()

    reward_target = 20.0
    balance = float(cust.points_balance or 0.0)
    points_to_reward = max(0.0, reward_target - balance)
    reward_progress_pct = min(100.0, (balance / reward_target * 100.0) if reward_target else 100.0)
    recent_rewards = RewardLedger.query.filter_by(customer_id=cust.id).order_by(RewardLedger.created_at.desc()).limit(8).all()
    referral_rewards_count = ReferralReward.query.filter_by(referrer_customer_id=cust.id).count()

    return render_template(
        'customer_dashboard.html',
        cust=cust,
        orders=my_orders,
        active_promos=active_promos,
        bonus_campaigns=bonus_campaigns,
        reward_target=reward_target,
        points_to_reward=points_to_reward,
        reward_progress_pct=reward_progress_pct,
        recent_rewards=recent_rewards,
        referral_rewards_count=referral_rewards_count,
        today=ph_today(),
    )

@app.route('/portal/suggest-product', methods=['POST'])
def customer_submit_product_suggestion():
    if 'customer_id' not in session:
        return redirect(url_for('customer_login', next='suggest'))

    cust = Customer.query.get_or_404(session['customer_id'])
    issue = customer_access_issue(cust)
    if issue:
        flash(issue, 'error')
        return redirect(url_for('customer_login'))

    suggestion_text = re.sub(r'\s+', ' ', request.form.get('suggestion', '').strip())
    if len(suggestion_text) < 2:
        flash('Please tell us what you would like Macleen\'s to offer.', 'error')
        return redirect(url_for('customer_dashboard') + '#suggest')
    if len(suggestion_text) > 500:
        flash('Please keep your suggestion to 500 characters or less.', 'error')
        return redirect(url_for('customer_dashboard') + '#suggest')

    db.session.add(ProductSuggestion(
        customer_id=cust.id,
        customer_name=cust.name,
        suggestion_text=suggestion_text,
        status='NEW',
    ))
    track_portal_event('PRODUCT_SUGGESTION', customer_id=cust.id)
    db.session.commit()
    flash('💡 Thank you! Your product suggestion was sent to Macleen\'s.', 'success')
    return redirect(url_for('customer_dashboard') + '#suggest')

@app.route('/portal/logout')
def customer_logout():
    if 'customer_id' in session:
        try:
            cust = Customer.query.get(session['customer_id'])
            if cust and hasattr(cust, 'last_active_at'):
                cust.last_active_at = utc_now() - timedelta(hours=1)
                db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.exception('Could not mark customer offline during logout')
    session.pop('customer_id', None)
    flash('Successfully logged out.', 'info')
    return redirect(url_for('store_catalog'))

@app.route('/portal/reserve-promo/<string:promo_code>', methods=['POST'])
def customer_reserve_promo_by_code(promo_code):
    if 'customer_id' not in session:
        return redirect(url_for('customer_login', next='deals'))

    cust = Customer.query.get_or_404(session['customer_id'])
    issue = customer_access_issue(cust)
    if issue:
        flash(issue, 'error')
        return redirect(url_for('customer_login'))
    promo = PromotionTracker.query.filter_by(promo_code=promo_code).first()

    if not promo or not promo.is_active or not promo.is_visible:
        flash('This promotion campaign is currently archived.', 'info')
        return redirect(url_for('customer_dashboard') + '#deals')

    days_active = (utc_now() - promo.created_at).days
    if days_active > 3:
        promo.is_active = False
        db.session.commit()
        flash('This 3-day promotion campaign has ended and is now archived.', 'info')
        return redirect(url_for('customer_dashboard') + '#deals')

    order = Order(
        order_type='PICKUP',
        dining_option='TAKEOUT',
        customer_id=cust.id,
        customer_name=f'{cust.name} (Member Promo)',
        contact_number=cust.contact,
        pickup_time='Today / In-Store Claim',
        target_time='In-Store Counter Claim',
        subtotal=promo.promo_price,
        delivery_fee=0.0,
        total_amount=promo.promo_price,
        payment_method='CASH',
        payment_verified=False,
        status='VERIFICATION',
        notes=f'[3-DAY PROMO CLAIM] {promo.title} (₱{promo.promo_price:,.2f} Deal)'
    )
    db.session.add(order)
    db.session.flush()

    db.session.add(OrderItem(
        order_id=order.id,
        product_id=None,
        product_name=f'[PROMO 3-DAY] {promo.title}',
        unit_price=promo.promo_price,
        cost_price=max(0.0, parse_float(promo.promo_cost, 0.0)),
        quantity=1,
        subtotal=promo.promo_price
    ))

    promo.claims_count = (promo.claims_count or 0) + 1
    promo.total_revenue = (promo.total_revenue or 0.0) + promo.promo_price
    track_portal_event('PROMO_RESERVE', customer_id=cust.id)
    db.session.commit()
    flash(f'🎉 Deal reserved! Order #{order.id} queued at Cashier counter.', 'success')
    return redirect(url_for('customer_dashboard') + '#deals')

@app.route('/portal/update-profile-pic', methods=['POST'])
def update_profile_pic():
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    cust = Customer.query.get(session['customer_id'])
    img_url = request.form.get('profile_image', '').strip()
    if img_url:
        cust.profile_image = img_url
        db.session.commit()
        flash('Profile picture updated!', 'success')
    return redirect(url_for('customer_dashboard'))

# ==================== INDEPENDENT STAFF AUTH ====================

@app.route('/staff/login', methods=['GET', 'POST'])
def staff_login():
    target = request.args.get('target', '').lower()
    if request.method == 'POST':
        user = request.form.get('username', '').strip().lower()
        pin = request.form.get('pin', '').strip()
        staff = Staff.query.filter(db.func.lower(Staff.username) == user).first()

        if staff and staff.active and check_password_hash(staff.pin_hash, pin):
            session.clear()
            session.permanent = False
            session['_staff_last_activity'] = utc_now().isoformat()
            if staff.role == 'ADMIN':
                session['admin_id'] = staff.id
                session['admin_user'] = staff.username
                return redirect(url_for('admin_dashboard'))
            if staff.role == 'CASHIER':
                session['cashier_id'] = staff.id
                session['cashier_user'] = staff.username
                return redirect(url_for('cashier_terminal'))
        flash('Invalid Username or PIN.', 'error')
    return render_template('staff_login.html', target=target)

@app.route('/staff/logout')
def staff_logout():
    clear_staff_session()
    flash('Logged out.', 'info')
    return redirect(url_for('staff_login'))

@app.route('/healthz')
def healthz():
    try:
        db.session.execute(text('SELECT 1'))
        return jsonify({'status': 'ok', 'time_ph': ph_now().isoformat()})
    except Exception:
        app.logger.exception('Health check failed')
        return jsonify({'status': 'error'}), 500

@app.errorhandler(500)
def internal_server_error(error):
    original = getattr(error, 'original_exception', None)
    app.logger.error('Unhandled server error on %s %s', request.method, request.path, exc_info=True)
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': 'Server error. Please try again.'}), 500
    return 'Macleen\'s Food House encountered a server error. Please try again.', 500

# Run schema/setup during application import so Render/Gunicorn fails visibly at startup if the DB is incompatible.
with app.app_context():
    run_db_setup()

if __name__ == '__main__':
    app.run(debug=True, port=5000)