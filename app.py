import os
import random
import string
from datetime import datetime, date, timedelta, time
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, inspect
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'macleens-hk-pos-2026-master')

database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///foodhouse_pos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=3650)

db = SQLAlchemy(app)

@app.before_request
def make_session_permanent():
    session.permanent = True
    if 'customer_id' in session:
        try:
            cust = Customer.query.get(session['customer_id'])
            if cust and hasattr(cust, 'last_active_at'):
                cust.last_active_at = datetime.utcnow()
                db.session.commit()
        except Exception:
            db.session.rollback()

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
    last_wifi_claim = db.Column(db.Date, nullable=True)
    wifi_voucher_code = db.Column(db.String(20), nullable=True)
    wifi_minutes_left = db.Column(db.Integer, default=10)
    last_active_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
    cost = db.Column(db.Float, default=0.0)
    stock = db.Column(db.Integer, default=100)
    image_url = db.Column(db.Text, nullable=True)
    is_featured = db.Column(db.Boolean, default=False)
    is_top_seller = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    available_start_time = db.Column(db.String(10), nullable=True)
    available_end_time = db.Column(db.String(10), nullable=True)
    total_likes = db.Column(db.Integer, default=0)
    comments = db.relationship('ProductComment', backref='product_rel', cascade="all, delete-orphan", lazy=True, order_by="desc(ProductComment.created_at)")

class ProductLike(db.Model):
    __tablename__ = 'product_like'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id', ondelete='CASCADE'), nullable=False)
    ip_address = db.Column(db.String(50), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ProductComment(db.Model):
    __tablename__ = 'product_comment'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id', ondelete='CASCADE'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id', ondelete='SET NULL'), nullable=True)
    author_name = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(50), nullable=False)
    comment_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    __tablename__ = 'order'
    id = db.Column(db.Integer, primary_key=True)
    order_type = db.Column(db.String(20), nullable=False)
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    customer = db.relationship('Customer', backref='orders', lazy=True)
    items = db.relationship('OrderItem', backref='order_rel', cascade="all, delete-orphan", lazy=True)

class OrderItem(db.Model):
    __tablename__ = 'order_item'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    product_name = db.Column(db.String(120), nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    cost_price = db.Column(db.Float, default=0.0)
    quantity = db.Column(db.Integer, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

class Expense(db.Model):
    __tablename__ = 'expense'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), default='General')
    created_by = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class VaultDrop(db.Model):
    __tablename__ = 'vault_drop'
    id = db.Column(db.Integer, primary_key=True)
    drop_number = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    notes = db.Column(db.String(255), nullable=True)
    cash_breakdown = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ChangeFund(db.Model):
    __tablename__ = 'change_fund'
    id = db.Column(db.Integer, primary_key=True)
    fund_title = db.Column(db.String(150), nullable=False, default="Cashier Opening Change Fund")
    amount = db.Column(db.Float, nullable=False)
    notes = db.Column(db.String(255), nullable=True)
    created_by = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class RewardLedger(db.Model):
    __tablename__ = 'reward_ledger'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    points_change = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(150), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SiteVisitor(db.Model):
    __tablename__ = 'site_visitor'
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(50), unique=True, nullable=False)
    visit_count = db.Column(db.Integer, default=1)
    visited_at = db.Column(db.DateTime, default=datetime.utcnow)

class PromotionTracker(db.Model):
    __tablename__ = 'promotion_tracker'
    id = db.Column(db.Integer, primary_key=True)
    promo_code = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(120), nullable=False)
    promo_price = db.Column(db.Float, nullable=False)
    promo_cost = db.Column(db.Float, default=0.0)
    page_views = db.Column(db.Integer, default=0)
    claims_count = db.Column(db.Integer, default=0)
    total_revenue = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ==================== PWA ROOT ROUTES ====================

@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'manifest.json', mimetype='application/manifest+json')

@app.route('/sw.js')
def serve_sw():
    response = send_from_directory(os.path.join(app.root_path, 'static'), 'sw.js', mimetype='application/javascript')
    response.headers['Service-Worker-Allowed'] = '/'
    return response

# ==================== HELPERS & GUARDS ====================

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or '127.0.0.1'

def get_store_settings():
    settings = {s.key: s.value for s in StoreSetting.query.all()}
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
    now_utc = datetime.utcnow()
    now_ph = (now_utc + timedelta(hours=8)).time()

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
        now_ph = (datetime.utcnow() + timedelta(hours=8)).time()
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
                promo_cost=28.0,
                page_views=0,
                claims_count=0,
                total_revenue=0.0,
                is_active=True
            ))

        deal2 = PromotionTracker.query.filter_by(promo_code='BEEFY_NACHOS_75').first()
        if not deal2:
            db.session.add(PromotionTracker(
                promo_code='BEEFY_NACHOS_75',
                title='All-New Loaded Beefy Nachos Supreme',
                promo_price=75.0,
                promo_cost=42.0,
                page_views=0,
                claims_count=0,
                total_revenue=0.0,
                is_active=True
            ))

        db.session.commit()
    except Exception:
        db.session.rollback()

@app.context_processor
def inject_globals():
    setting = StoreSetting.query.filter_by(key='logo_url').first()
    status = check_operating_status()
    return dict(
        store_logo=setting.value if setting else '/static/logo.png',
        status=status
    )

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_user'):
            return redirect(url_for('staff_login', target='admin'))
        return f(*args, **kwargs)
    return decorated

def require_cashier(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not (session.get('cashier_user') or session.get('admin_user')):
            return redirect(url_for('staff_login', target='cashier'))
        return f(*args, **kwargs)
    return decorated

# ==================== REAL-TIME POLLING API ====================

@app.route('/api/queue-counts')
def api_queue_counts():
    pending_cashier = Order.query.filter_by(status="VERIFICATION").count()
    return jsonify({
        'pending_cashier': pending_cashier
    })

# ==================== STOREFRONT ====================

@app.route('/')
def store_catalog():
    ensure_default_promos()
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

    unique_visitors = SiteVisitor.query.count()
    total_accumulated_visits = db.session.query(db.func.coalesce(db.func.sum(SiteVisitor.visit_count), 0)).scalar() or unique_visitors

    categories = Category.query.all()
    all_active_products = Product.query.filter_by(is_active=True).all()
    available_products = [p for p in all_active_products if is_product_available_now(p)]

    featured = [p for p in available_products if p.is_featured]
    top_sellers = [p for p in available_products if p.is_top_seller]
    products = sorted(available_products, key=lambda x: (-(x.total_likes or 0), x.id))

    liked_ids = {pl.product_id for pl in ProductLike.query.filter_by(ip_address=get_client_ip()).all()}
    delivery_zones = DeliveryZone.query.filter_by(is_active=True).all()
    status = check_operating_status()
    active_promos = PromotionTracker.query.filter_by(is_active=True).all()

    cust = None
    if 'customer_id' in session:
        cust = Customer.query.get(session['customer_id'])

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
                           total_accumulated_visits=total_accumulated_visits)

@app.route('/promo/burger-deal')
def promo_burger_deal():
    ensure_default_promos()
    promo = PromotionTracker.query.filter_by(promo_code='BURGER_FRIES_50').first()
    if promo:
        promo.page_views = (promo.page_views or 0) + 1
        db.session.commit()
    return render_template('promo_burger_deal.html')

@app.route('/promo/beefy-nachos')
def promo_beefy_nachos():
    ensure_default_promos()
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
    text = data.get('comment', '').strip()
    if not text:
        return jsonify({'success': False, 'message': 'Comment cannot be empty.'}), 400

    name = f"Guest ({ip})"
    if cust_id:
        cust = Customer.query.get(cust_id)
        if cust:
            name = cust.name

    comment = ProductComment(product_id=product_id, customer_id=cust_id, author_name=name, ip_address=ip, comment_text=text)
    db.session.add(comment)
    db.session.commit()
    return jsonify({'success': True, 'author': name, 'comment': text, 'created_at': 'Just now'})

@app.route('/api/storefront-checkout', methods=['POST'])
def api_storefront_checkout():
    if 'customer_id' not in session:
        return jsonify({'success': False, 'message': 'Registration / Login is required. No guest checkout.'}), 403

    status = check_operating_status()
    cust = Customer.query.get(session['customer_id'])
    data = request.get_json() or {}
    items = data.get('items', [])
    order_type = data.get('order_type', 'PICKUP').upper()
    pay_method = data.get('payment_method', 'CASH').upper()
    notes = data.get('notes', '').strip() or 'None'
    target_time = data.get('target_time', '').strip()
    zone_id = data.get('delivery_zone_id')
    landmark = data.get('landmark', '').strip()
    delivery_address = data.get('delivery_address', '').strip()
    gcash_ref = data.get('gcash_ref', '').strip()
    fb = data.get('fb_messenger', '').strip()

    if order_type == 'PICKUP' and not status['store_open']:
        return jsonify({'success': False, 'message': 'Store ordering is currently closed.'}), 400

    if order_type == 'DELIVERY' and not status['delivery_open']:
        return jsonify({'success': False, 'message': 'Barangay delivery is currently unavailable/closed.'}), 400

    if not items or not target_time:
        return jsonify({'success': False, 'message': 'Please complete your target time and select cart items.'}), 400

    delivery_fee = 0.0
    final_address = delivery_address
    final_landmark = landmark

    if order_type == 'DELIVERY':
        if not zone_id and (not landmark or not delivery_address):
            return jsonify({'success': False, 'message': 'Please choose a Barangay Delivery Zone or provide address info.'}), 400
        if zone_id:
            zone = DeliveryZone.query.get(zone_id)
            if zone:
                delivery_fee = zone.rate
                final_address = f"Barangay: {zone.barangay} ({zone.place_name})"
                final_landmark = landmark or zone.note or "Designated Delivery Spot"

    if pay_method == 'CREDIT' and not cust.is_credit_eligible:
        return jsonify({'success': False, 'message': 'Your account is not authorized for A/R Credit.'}), 403

    if pay_method in ['GCASH', 'CREDIT'] and not fb:
        return jsonify({'success': False, 'message': 'Facebook messenger link is required for evaluation.'}), 400

    if pay_method == 'GCASH' and len(gcash_ref) < 6:
        return jsonify({'success': False, 'message': 'Please input the 6-digit GCash Reference Number.'}), 400

    subtotal = sum(Product.query.get(it['product_id']).price * int(it['quantity']) for it in items if Product.query.get(it['product_id']))
    total = subtotal + delivery_fee

    order = Order(
        order_type=order_type,
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
    )
    db.session.add(order)
    db.session.flush()

    for it in items:
        prod = Product.query.get(it['product_id'])
        if prod:
            db.session.add(OrderItem(
                order_id=order.id, product_id=prod.id, product_name=prod.name,
                unit_price=prod.price, cost_price=prod.cost, quantity=int(it['quantity']),
                subtotal=prod.price * int(it['quantity'])
            ))
            if prod.stock >= int(it['quantity']):
                prod.stock -= int(it['quantity'])

    db.session.commit()
    return jsonify({'success': True, 'order_id': order.id, 'total': total})

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
    items = data.get('items', [])
    customer_name = data.get('customer_name', 'Tablet Kiosk Guest').strip() or 'Tablet Kiosk Guest'
    pay_method = data.get('payment_method', 'CASH').upper()
    notes = data.get('notes', 'Tablet Self-Order').strip() or 'Tablet Self-Order'

    if not items:
        return jsonify({'success': False, 'message': 'Ticket is empty.'}), 400

    cust_id = None
    contact_num = 'Kiosk'
    if 'PIN:' in customer_name:
        pin_code = customer_name.split('PIN:')[1].replace(')', '').strip()
        matched = Customer.query.filter((Customer.contact == pin_code) | (Customer.card_number == pin_code)).first()
        if matched:
            cust_id = matched.id
            customer_name = matched.name
            contact_num = matched.contact

    subtotal = sum(Product.query.get(it['product_id']).price * int(it['quantity']) for it in items if Product.query.get(it['product_id']))

    order = Order(
        order_type='TABLET',
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
    )
    db.session.add(order)
    db.session.flush()

    for it in items:
        prod = Product.query.get(it['product_id'])
        if prod:
            db.session.add(OrderItem(
                order_id=order.id,
                product_id=prod.id,
                product_name=prod.name,
                unit_price=prod.price,
                cost_price=prod.cost,
                quantity=int(it['quantity']),
                subtotal=prod.price * int(it['quantity'])
            ))
            if prod.stock >= int(it['quantity']):
                prod.stock -= int(it['quantity'])

    db.session.commit()
    return jsonify({'success': True, 'order_id': order.id, 'total': subtotal})

# ==================== CASHIER TERMINAL & CLAIM DISPATCH ====================

@app.route('/pos/cashier')
@require_cashier
def cashier_terminal():
    ensure_default_promos()
    categories = Category.query.all()
    products = Product.query.filter_by(is_active=True).all()
    pending_orders = Order.query.filter_by(status="VERIFICATION").order_by(Order.created_at.asc()).all()
    completed_orders = Order.query.filter_by(status="COMPLETED").order_by(Order.created_at.desc()).limit(15).all()
    unpaid_collections = Order.query.filter_by(is_unpaid=True).order_by(Order.created_at.desc()).all()
    today_wifi_claims = Customer.query.filter_by(last_wifi_claim=date.today()).all()
    staff_list = Staff.query.all()
    customers_list = Customer.query.order_by(Customer.name.asc()).all()

    two_mins_ago = datetime.utcnow() - timedelta(minutes=2)
    try:
        online_customers = Customer.query.filter(Customer.last_active_at >= two_mins_ago).order_by(Customer.last_active_at.desc()).all()
    except Exception:
        online_customers = []

    credit_customers = Customer.query.filter(Customer.outstanding_ar > 0).order_by(Customer.outstanding_ar.desc()).all()

    today = date.today()
    today_expenses = Expense.query.filter(db.func.date(Expense.created_at) == today).order_by(Expense.created_at.desc()).all()
    today_drops = VaultDrop.query.filter(db.func.date(VaultDrop.created_at) == today).order_by(VaultDrop.drop_number.asc()).all()
    try:
        today_change_funds = ChangeFund.query.filter(db.func.date(ChangeFund.created_at) == today).order_by(ChangeFund.created_at.desc()).all()
    except Exception:
        today_change_funds = []
    next_drop_num = len(today_drops) + 1

    return render_template('cashier_pos.html', 
                           categories=categories, 
                           products=products, 
                           pending_orders=pending_orders, 
                           completed_orders=completed_orders,
                           unpaid_collections=unpaid_collections,
                           credit_customers=credit_customers,
                           online_customers=online_customers,
                           today_wifi_claims=today_wifi_claims,
                           staff_list=staff_list,
                           customers_list=customers_list,
                           today_expenses=today_expenses,
                           today_drops=today_drops,
                           today_change_funds=today_change_funds,
                           next_drop_num=next_drop_num)

@app.route('/pos/direct-sale', methods=['POST'])
@require_cashier
def cashier_direct_sale():
    data = request.get_json() or {}
    items = data.get('items', [])
    cust_type = data.get('customer_type', 'WALKIN')
    reg_id = data.get('registered_customer_id')
    pay_method = data.get('payment_method', 'CASH').upper()
    cust_name = data.get('customer_name', 'Counter Walk-in').strip() or 'Counter Walk-in'
    notes = data.get('notes', 'Cashier Counter POS Sale').strip() or 'Cashier Counter POS Sale'
    change_for = float(data.get('change_for') or 0.0)

    if not items:
        return jsonify({'success': False, 'message': 'No items in cart.'}), 400

    subtotal = sum(Product.query.get(it['product_id']).price * int(it['quantity']) for it in items if Product.query.get(it['product_id']))

    cust_id = None
    contact = 'N/A'
    points_earned = 0

    if cust_type == 'REGISTERED' and reg_id:
        cust = Customer.query.get(reg_id)
        if cust:
            cust_id = cust.id
            cust_name = cust.name
            contact = cust.contact
            cust.accumulated_spend = (cust.accumulated_spend or 0.0) + subtotal
            points_earned = int(subtotal // 30)
            if points_earned > 0:
                cust.points_balance = (cust.points_balance or 0.0) + points_earned
                db.session.add(RewardLedger(
                    customer_id=cust.id,
                    points_change=points_earned,
                    reason=f"Counter POS Sale (₱{subtotal:,.2f})"
                ))

    order = Order(
        order_type='DINE-IN/WALKIN',
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
    )
    db.session.add(order)
    db.session.flush()

    for it in items:
        prod = Product.query.get(it['product_id'])
        if prod:
            db.session.add(OrderItem(
                order_id=order.id,
                product_id=prod.id,
                product_name=prod.name,
                unit_price=prod.price,
                cost_price=prod.cost,
                quantity=int(it['quantity']),
                subtotal=prod.price * int(it['quantity'])
            ))
            if prod.stock >= int(it['quantity']):
                prod.stock -= int(it['quantity'])

    db.session.commit()
    return jsonify({
        'success': True,
        'order_id': order.id,
        'total': subtotal,
        'points_earned': points_earned
    })

@app.route('/pos/claim-promo', methods=['POST'])
@require_cashier
def cashier_claim_promo():
    ensure_default_promos()
    promo_code = request.form.get('promo_code', 'BURGER_FRIES_50')
    reg_id = request.form.get('registered_customer_id')
    pay_method = request.form.get('payment_method', 'CASH').upper()
    
    promo = PromotionTracker.query.filter_by(promo_code=promo_code).first()
    if not promo:
        flash("Promotion deal not found.", "error")
        return redirect(url_for('cashier_terminal'))

    cust_id = None
    cust_name = 'Walk-in Member'
    contact = 'N/A'
    points_earned = 0

    if reg_id:
        cust = Customer.query.get(reg_id)
        if cust:
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
        cost_price=promo.promo_cost,
        quantity=1,
        subtotal=promo.promo_price
    ))

    promo.claims_count = (promo.claims_count or 0) + 1
    promo.total_revenue = (promo.total_revenue or 0.0) + promo.promo_price

    db.session.commit()
    flash(f"🎉 Promo Deal '{promo.title}' recorded for {cust_name} (₱{promo.promo_price:,.2f})!", "success")
    return redirect(url_for('cashier_terminal'))

@app.route('/pos/misc-sale', methods=['POST'])
@require_cashier
def cashier_misc_sale():
    service_name = request.form.get('service_name', '').strip() or 'Printing / Custom Service'
    amount = float(request.form.get('amount') or 0.0)
    pay_method = request.form.get('payment_method', 'CASH')
    notes = request.form.get('notes', '').strip() or 'Over-the-counter Misc Service'
    reg_cust_id = request.form.get('registered_customer_id')
    custom_name = request.form.get('custom_customer_name', '').strip()

    if amount <= 0:
        flash("Amount must be greater than zero.", "error")
        return redirect(url_for('cashier_terminal'))

    cust_id = None
    customer_name = 'Walk-in Customer'
    contact = 'N/A'

    if reg_cust_id:
        cust = Customer.query.get(reg_cust_id)
        if cust:
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

    db.session.commit()
    flash(f"Misc Sale recorded: {service_name} for {customer_name} (₱{amount:,.2f})", "success")
    return redirect(url_for('cashier_terminal'))

@app.route('/pos/record-change-fund', methods=['POST'])
@require_cashier
def cashier_record_change_fund():
    title = request.form.get('fund_title', 'Opening Petty/Change Fund').strip()
    amount = float(request.form.get('amount') or 0.0)
    notes = request.form.get('notes', 'Ulam / Register Drawer Starting Cash').strip()
    staff_user = session.get('cashier_user') or session.get('admin_user') or 'Cashier'

    if amount <= 0:
        flash("Change fund amount must be greater than zero.", "error")
        return redirect(url_for('cashier_terminal'))

    db.session.add(ChangeFund(fund_title=title, amount=amount, notes=notes, created_by=staff_user))
    db.session.commit()
    flash(f"Change Fund (₱{amount:,.2f}) added to register drawer notes. (Excluded from Sales/Revenue)", "success")
    return redirect(url_for('cashier_terminal'))

@app.route('/pos/create-collection', methods=['POST'])
@require_cashier
def cashier_create_collection():
    cust_type = request.form.get('customer_type', 'REGISTERED')
    item_choice_type = request.form.get('item_choice_type', 'PRODUCT')
    product_id = request.form.get('product_id')
    qty = int(request.form.get('quantity') or 1)
    notes = request.form.get('notes', '').strip()
    
    prod_name = 'Custom Receivable Item'
    unit_p = float(request.form.get('custom_amount') or 0.0)
    cost_p = 0.0

    if item_choice_type == 'PRODUCT' and product_id:
        prod = Product.query.get(int(product_id))
        if prod:
            prod_name = prod.name
            unit_p = prod.price
            cost_p = prod.cost
    else:
        prod_name = request.form.get('custom_title', '').strip() or 'Custom Receivable Service'

    amount = unit_p * qty

    if amount <= 0:
        flash("Amount must be greater than zero.", "error")
        return redirect(url_for('cashier_terminal'))

    cust_id = None
    cust_name = 'Walk-in Customer'
    contact = 'N/A'

    if cust_type == 'REGISTERED':
        reg_id = request.form.get('registered_customer_id')
        if reg_id:
            cust = Customer.query.get(reg_id)
            if cust:
                cust_id = cust.id
                cust_name = cust.name
                contact = cust.contact
                cust.outstanding_ar = (cust.outstanding_ar or 0.0) + amount
    else:
        cust_name = request.form.get('custom_customer_name', '').strip() or 'Custom Account'
        contact = request.form.get('custom_contact', '').strip() or 'N/A'

    order = Order(
        order_type='COLLECTION',
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
        notes=f"Attributable Item: {prod_name} (x{qty})"
    )
    db.session.add(order)
    db.session.flush()

    db.session.add(OrderItem(
        order_id=order.id,
        product_id=int(product_id) if (item_choice_type == 'PRODUCT' and product_id) else None,
        product_name=prod_name,
        unit_price=unit_p,
        cost_price=cost_p,
        quantity=qty,
        subtotal=amount
    ))

    db.session.commit()
    flash(f"For Collection order recorded for {cust_name}: {prod_name} x{qty} (₱{amount:,.2f})", "info")
    return redirect(url_for('cashier_terminal'))

@app.route('/pos/settle-collection/<int:order_id>', methods=['POST'])
@require_cashier
def cashier_settle_collection(order_id):
    order = Order.query.get_or_404(order_id)
    pay_method = request.form.get('payment_method', 'CASH')
    
    order.is_unpaid = False
    order.status = 'COMPLETED'
    order.payment_method = pay_method
    order.payment_verified = True

    is_same_day = (order.created_at.date() == datetime.utcnow().date())
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

    db.session.commit()
    bonus_msg = f" (+{earned} pts earned for Same-Day payment!)" if earned > 0 else " (No points: paid after order date)"
    flash(f"Collection #{order.id} for {order.customer_name} settled via {pay_method}!{bonus_msg}", "success")
    return redirect(url_for('cashier_terminal'))

@app.route('/pos/settle-customer-credit/<int:cust_id>', methods=['POST'])
@require_cashier
def cashier_settle_customer_credit(cust_id):
    cust = Customer.query.get_or_404(cust_id)
    amount = float(request.form.get('amount') or cust.outstanding_ar)
    pay_method = request.form.get('payment_method', 'CASH').upper()

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
    amount = float(request.form.get('amount') or 0.0)
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
    drop_num = int(request.form.get('drop_number') or 1)
    amount = float(request.form.get('amount') or 0.0)
    notes = request.form.get('notes', '').strip()
    breakdown = request.form.get('cash_breakdown', '').strip()
    staff_user = session.get('cashier_user') or session.get('admin_user') or 'Cashier'

    if amount <= 0:
        flash("Drop amount must be greater than zero.", "error")
        return redirect(url_for('cashier_terminal'))

    db.session.add(VaultDrop(drop_number=drop_num, amount=amount, notes=notes, cash_breakdown=breakdown, created_by=staff_user))
    db.session.commit()
    flash(f"Vault Cash Drop #{drop_num} recorded: ₱{amount:,.2f}", "success")
    return redirect(url_for('cashier_terminal'))

@app.route('/pos/update-wifi-minutes/<int:cust_id>', methods=['POST'])
@require_cashier
def cashier_update_wifi_minutes(cust_id):
    cust = Customer.query.get_or_404(cust_id)
    mins = request.form.get('wifi_minutes')
    if mins is not None:
        try:
            cust.wifi_minutes_left = max(0, int(mins))
            db.session.commit()
            flash(f"Updated Wi-Fi time for {cust.name} to {cust.wifi_minutes_left} mins.", "success")
        except ValueError:
            flash("Invalid minutes entered.", "error")
    return redirect(url_for('cashier_terminal'))

@app.route('/pos/verify/<int:order_id>', methods=['POST'])
@require_cashier
def verify_order(order_id):
    order = Order.query.get_or_404(order_id)
    action = request.form.get('action')

    if action == 'ACCEPT':
        order.payment_verified = True
        order.status = "COMPLETED"

        if order.customer_id and order.payment_method != "CREDIT":
            cust = Customer.query.get(order.customer_id)
            if cust:
                cust.accumulated_spend = (cust.accumulated_spend or 0.0) + order.total_amount
                earned = int(order.total_amount // 30)
                if earned > 0:
                    cust.points_balance = (cust.points_balance or 0.0) + earned
                    db.session.add(RewardLedger(customer_id=cust.id, points_change=earned, reason=f"Purchase Order #{order.id}"))

        db.session.commit()
        flash(f"Order #{order.id} accepted and completed. Details ready to print!", "success")
    else:
        for item in order.items:
            if item.product_id:
                prod = Product.query.get(item.product_id)
                if prod:
                    prod.stock += item.quantity
        order.status = "CANCELLED"
        db.session.commit()
        flash(f"Order #{order.id} cancelled.", "info")

    return redirect(url_for('cashier_terminal'))

# ==================== MASTER ADMIN, CONTROLS & SETTINGS ====================

@app.route('/admin')
@require_admin
def admin_dashboard():
    ensure_default_promos()
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

    unique_visitors = SiteVisitor.query.count()
    total_accumulated_visits = db.session.query(db.func.coalesce(db.func.sum(SiteVisitor.visit_count), 0)).scalar() or unique_visitors

    today = date.today()
    week_ago = datetime.utcnow() - timedelta(days=7)
    month_ago = datetime.utcnow() - timedelta(days=30)

    daily_orders = Order.query.filter(db.func.date(Order.created_at) == today, Order.status == 'COMPLETED').all()
    weekly_orders = Order.query.filter(Order.created_at >= week_ago, Order.status == 'COMPLETED').all()
    monthly_orders = Order.query.filter(Order.created_at >= month_ago, Order.status == 'COMPLETED').all()
    all_completed = Order.query.filter_by(status='COMPLETED').all()

    daily_exp = db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0.0)).filter(db.func.date(Expense.created_at) == today).scalar() or 0.0
    weekly_exp = db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0.0)).filter(Expense.created_at >= week_ago).scalar() or 0.0
    monthly_exp = db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0.0)).filter(Expense.created_at >= month_ago).scalar() or 0.0
    total_exp_all = sum(e.amount for e in all_expenses)

    daily_vault = db.session.query(db.func.coalesce(db.func.sum(VaultDrop.amount), 0.0)).filter(db.func.date(VaultDrop.created_at) == today).scalar() or 0.0
    weekly_vault = db.session.query(db.func.coalesce(db.func.sum(VaultDrop.amount), 0.0)).filter(VaultDrop.created_at >= week_ago).scalar() or 0.0
    monthly_vault = db.session.query(db.func.coalesce(db.func.sum(VaultDrop.amount), 0.0)).filter(VaultDrop.created_at >= month_ago).scalar() or 0.0
    all_vault = db.session.query(db.func.coalesce(db.func.sum(VaultDrop.amount), 0.0)).scalar() or 0.0

    def calc_period(orders, exp, vault_drop_sales):
        order_rev = sum(o.total_amount for o in orders)
        total_rev = order_rev + vault_drop_sales
        cost = sum(sum((it.cost_price or 0.0) * it.quantity for it in o.items) for o in orders)
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
    for o in all_completed:
        for it in o.items:
            pname = it.product_name
            if pname not in product_sales_stats:
                product_sales_stats[pname] = {'qty': 0, 'revenue': 0.0, 'cost': 0.0}
            product_sales_stats[pname]['qty'] += (it.quantity or 0)
            product_sales_stats[pname]['revenue'] += (it.subtotal or 0.0)
            product_sales_stats[pname]['cost'] += (it.cost_price or 0.0) * (it.quantity or 0)

    total_ar = sum((c.outstanding_ar or 0.0) for c in customers)

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
                           unique_visitors=unique_visitors, 
                           total_accumulated_visits=total_accumulated_visits,
                           fin_daily=fin_daily,
                           fin_weekly=fin_weekly,
                           fin_monthly=fin_monthly,
                           fin_all=fin_all,
                           total_ar=total_ar,
                           current_sort=sort_by)

@app.route('/admin/allocate-vault-drop/<int:drop_id>', methods=['POST'])
@require_admin
def admin_allocate_vault_drop(drop_id):
    drop = VaultDrop.query.get_or_404(drop_id)
    cust_id = request.form.get('customer_id')
    product_id = request.form.get('product_id')
    allocated_amount = float(request.form.get('amount') or 0.0)
    qty = int(request.form.get('quantity') or 1)

    if allocated_amount <= 0 or allocated_amount > drop.amount:
        flash("Allocated amount must be between ₱0.01 and the remaining drop balance.", "error")
        return redirect(url_for('admin_dashboard'))

    cust = Customer.query.get(int(cust_id)) if cust_id else None
    prod = Product.query.get(int(product_id)) if product_id else None

    drop.amount = max(0.0, drop.amount - allocated_amount)

    order = Order(
        order_type='ALLOCATED_VAULT_SALE',
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
        cost_price=prod.cost if prod else 0.0,
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
    old_cust = Customer.query.get(order.customer_id) if order.customer_id else None

    if old_cust and order.status == 'COMPLETED':
        earned = int(order.total_amount // 30)
        old_cust.points_balance = max(0.0, (old_cust.points_balance or 0.0) - earned)
        old_cust.accumulated_spend = max(0.0, (old_cust.accumulated_spend or 0.0) - order.total_amount)

    order.customer_id = new_cust.id
    order.customer_name = new_cust.name
    order.contact_number = new_cust.contact

    if order.status == 'COMPLETED':
        earned_new = int(order.total_amount // 30)
        new_cust.accumulated_spend = (new_cust.accumulated_spend or 0.0) + order.total_amount
        if earned_new > 0:
            new_cust.points_balance = (new_cust.points_balance or 0.0) + earned_new
            db.session.add(RewardLedger(
                customer_id=new_cust.id,
                points_change=earned_new,
                reason=f"Admin Reassigned Order #{order.id}"
            ))

    db.session.commit()
    flash(f"Transaction #{order.id} reassigned to '{new_cust.name}'.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update-expense/<int:expense_id>', methods=['POST'])
@require_admin
def admin_update_expense(expense_id):
    exp = Expense.query.get_or_404(expense_id)
    exp.title = request.form.get('title', exp.title).strip()
    exp.amount = float(request.form.get('amount') or exp.amount)
    exp.category = request.form.get('category', exp.category).strip()
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

    if order.customer_id and order.status == 'COMPLETED':
        cust = Customer.query.get(order.customer_id)
        if cust:
            earned = int(order.total_amount // 30)
            cust.points_balance = max(0.0, (cust.points_balance or 0.0) - earned)
            cust.accumulated_spend = max(0.0, (cust.accumulated_spend or 0.0) - order.total_amount)
            db.session.add(RewardLedger(
                customer_id=cust.id,
                points_change=-earned,
                reason=f"Admin Reverted Sale #{order.id}"
            ))

    if order.is_unpaid and order.customer_id:
        cust = Customer.query.get(order.customer_id)
        if cust:
            cust.outstanding_ar = max(0.0, (cust.outstanding_ar or 0.0) - order.total_amount)

    db.session.delete(order)
    db.session.commit()
    flash(f"Order #{order_id} has been completely deleted & reverted (inventory and points restored).", "info")
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
    flash(f"Purged test orders & reset points for dummy account '{cust.name}'.", "info")
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
    flash(f"Account '{cust.name}' and all associated test data permanently removed.", "success")
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

@app.route('/portal/accounting')
@require_admin
def accounting_portal():
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add-product', methods=['POST'])
@require_admin
def admin_add_product():
    name = request.form.get('name')
    category_name = request.form.get('category_name')
    price = float(request.form.get('price') or 0.0)
    cost = float(request.form.get('cost') or 0.0)
    stock = int(request.form.get('stock') or 100)
    image_url = request.form.get('image_url', '').strip()
    start_t = request.form.get('available_start_time', '').strip() or None
    end_t = request.form.get('available_end_time', '').strip() or None
    is_featured = bool(request.form.get('is_featured'))
    is_top_seller = bool(request.form.get('is_top_seller'))

    db.session.add(Product(name=name, category_name=category_name, price=price, cost=cost, stock=stock, 
                           image_url=image_url, available_start_time=start_t, available_end_time=end_t,
                           is_featured=is_featured, is_top_seller=is_top_seller))
    db.session.commit()
    flash(f"Product '{name}' added.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/batch-update-products', methods=['POST'])
@require_admin
def admin_batch_update_products():
    for pid in request.form.getlist('product_id'):
        prod = Product.query.get(pid)
        if prod:
            prod.price = float(request.form.get(f'price_{pid}') or prod.price)
            prod.cost = float(request.form.get(f'cost_{pid}') or prod.cost)
            prod.stock = int(request.form.get(f'stock_{pid}') or prod.stock)
            prod.image_url = request.form.get(f'image_url_{pid}', '').strip()
            prod.available_start_time = request.form.get(f'available_start_time_{pid}', '').strip() or None
            prod.available_end_time = request.form.get(f'available_end_time_{pid}', '').strip() or None
            prod.is_active = (f'is_active_{pid}' in request.form)
            prod.is_featured = (f'is_featured_{pid}' in request.form)
            prod.is_top_seller = (f'is_top_seller_{pid}' in request.form)
    db.session.commit()
    flash("Bulk product catalog updated.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/toggle-credit/<int:cust_id>', methods=['POST'])
@require_admin
def admin_toggle_credit(cust_id):
    cust = Customer.query.get_or_404(cust_id)
    cust.is_credit_eligible = not cust.is_credit_eligible
    limit = request.form.get('credit_limit')
    if limit:
        cust.credit_limit = float(limit)
    db.session.commit()
    flash(f"Credit eligibility updated for {cust.name}.", "success")
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

@app.route('/admin/reset-customer-pin/<int:cust_id>', methods=['POST'])
@require_admin
def admin_reset_customer_pin(cust_id):
    cust = Customer.query.get_or_404(cust_id)
    new_pin = request.form.get('new_pin', '').strip()
    if not new_pin or len(new_pin) < 4:
        flash("PIN must be at least 4 digits.", "error")
    else:
        cust.pin_hash = generate_password_hash(new_pin)
        db.session.commit()
        flash(f"PIN for customer '{cust.name}' reset to {new_pin}.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/toggle-promo/<int:promo_id>', methods=['POST'])
@require_admin
def admin_toggle_promo(promo_id):
    promo = PromotionTracker.query.get_or_404(promo_id)
    promo.is_active = not promo.is_active
    if promo.is_active:
        promo.created_at = datetime.utcnow()
    db.session.commit()
    flash(f"Campaign '{promo.title}' status updated to {'ACTIVE' if promo.is_active else 'ARCHIVED'}.", "success")
    return redirect(url_for('admin_dashboard'))

# ==================== CUSTOMER PORTAL ====================

@app.route('/portal/login', methods=['GET', 'POST'])
def customer_login():
    if request.method == 'POST':
        contact = request.form.get('contact', '').strip()
        pin = request.form.get('pin', '').strip()
        cust = Customer.query.filter_by(contact=contact).first()
        if cust and check_password_hash(cust.pin_hash, pin):
            session['customer_id'] = cust.id
            if hasattr(cust, 'last_active_at'):
                cust.last_active_at = datetime.utcnow()
            db.session.commit()
            return redirect(url_for('customer_dashboard'))
        flash("Invalid Contact or PIN.", "error")
    return render_template('customer_login.html')

@app.route('/portal/register', methods=['GET', 'POST'])
def customer_register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        contact = request.form.get('contact', '').strip()
        messenger = request.form.get('fb_messenger', '').strip()
        pin = request.form.get('pin', '').strip()
        address = request.form.get('default_address', '').strip()
        landmark = request.form.get('default_landmark', '').strip()

        if Customer.query.filter_by(contact=contact).first():
            flash("Contact number already registered.", "error")
            return redirect(url_for('customer_register'))

        total_registered_cust = Customer.query.count()
        starting_bonus_points = 5.0 if total_registered_cust < 11 else 0.0

        new_cust = Customer(
            name=name,
            email=email,
            contact=contact,
            fb_messenger=messenger,
            default_address=address,
            default_landmark=landmark,
            points_balance=starting_bonus_points,
            pin_hash=generate_password_hash(pin),
            card_number=f"MFH-{random.randint(1, 100):04d}",
            card_expires_at=date.today() + timedelta(days=365),
            last_active_at=datetime.utcnow()
        )
        db.session.add(new_cust)
        db.session.flush()

        if starting_bonus_points > 0:
            db.session.add(RewardLedger(
                customer_id=new_cust.id,
                points_change=5.0,
                reason="Early Bird Launch Bonus (First 11 Registrants)"
            ))

        db.session.commit()
        session['customer_id'] = new_cust.id

        if starting_bonus_points > 0:
            flash("🎉 Congratulations! You are one of the first 11 registrants and earned 5 BONUS points!", "success")
            
        return redirect(url_for('customer_dashboard'))
    return render_template('customer_register.html')

@app.route('/portal/dashboard')
def customer_dashboard():
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    
    ensure_default_promos()
    cust = Customer.query.get(session['customer_id'])
    if not cust:
        session.pop('customer_id', None)
        flash("Account session expired. Please log in again.", "info")
        return redirect(url_for('customer_login'))
    
    my_orders = Order.query.filter_by(customer_id=cust.id).order_by(Order.created_at.desc()).all()
    promo_burger = PromotionTracker.query.filter_by(promo_code='BURGER_FRIES_50').first()
    promo_nachos = PromotionTracker.query.filter_by(promo_code='BEEFY_NACHOS_75').first()
    
    return render_template('customer_dashboard.html', 
                           cust=cust, 
                           orders=my_orders, 
                           promo_burger=promo_burger, 
                           promo_nachos=promo_nachos, 
                           today=date.today())

@app.route('/portal/logout')
def customer_logout():
    if 'customer_id' in session:
        try:
            cust = Customer.query.get(session['customer_id'])
            if cust and hasattr(cust, 'last_active_at'):
                cust.last_active_at = datetime.utcnow() - timedelta(hours=1)
                db.session.commit()
        except Exception:
            db.session.rollback()
    session.pop('customer_id', None)
    flash("Successfully logged out.", "info")
    return redirect(url_for('store_catalog'))

@app.route('/portal/reserve-promo/<string:promo_code>', methods=['POST'])
def customer_reserve_promo_by_code(promo_code):
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    
    ensure_default_promos()
    cust = Customer.query.get_or_404(session['customer_id'])
    promo = PromotionTracker.query.filter_by(promo_code=promo_code).first()

    if not promo or not promo.is_active:
        flash("This promotion campaign is currently archived.", "info")
        return redirect(url_for('customer_dashboard'))

    days_active = (datetime.utcnow() - promo.created_at).days
    if days_active > 3:
        promo.is_active = False
        db.session.commit()
        flash("This 3-day promotion campaign has ended and is now archived.", "info")
        return redirect(url_for('customer_dashboard'))

    order = Order(
        order_type='PICKUP',
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
    )
    db.session.add(order)
    db.session.flush()

    db.session.add(OrderItem(
        order_id=order.id,
        product_id=None,
        product_name=f"[PROMO 3-DAY] {promo.title}",
        unit_price=promo.promo_price,
        cost_price=promo.promo_cost,
        quantity=1,
        subtotal=promo.promo_price
    ))

    promo.claims_count = (promo.claims_count or 0) + 1
    promo.total_revenue = (promo.total_revenue or 0.0) + promo.promo_price

    db.session.commit()
    flash(f"🎉 Deal reserved! Order #{order.id} sent to Cashier. Pay ₱{promo.promo_price:,.2f} at the counter upon claiming!", "success")
    return redirect(url_for('customer_dashboard'))

@app.route('/portal/update-profile-pic', methods=['POST'])
def update_profile_pic():
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    cust = Customer.query.get(session['customer_id'])
    img_url = request.form.get('profile_image', '').strip()
    if img_url:
        cust.profile_image = img_url
        db.session.commit()
        flash("Profile picture updated!", "success")
    return redirect(url_for('customer_dashboard'))

@app.route('/portal/claim-wifi', methods=['POST'])
def claim_daily_wifi():
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    cust = Customer.query.get(session['customer_id'])

    if cust.last_wifi_claim == date.today():
        flash(f"Today's Wi-Fi already claimed: {cust.wifi_voucher_code}", "info")
    else:
        voucher = "MFH-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        cust.last_wifi_claim = date.today()
        cust.wifi_voucher_code = voucher
        cust.wifi_minutes_left = 10
        db.session.commit()
        flash(f"Claimed 10-Mins Free Wi-Fi! Passcode: {voucher}", "success")
    return redirect(url_for('customer_dashboard'))

# ==================== INDEPENDENT STAFF AUTH ====================

@app.route('/staff/login', methods=['GET', 'POST'])
def staff_login():
    target = request.args.get('target', '').lower()
    if request.method == 'POST':
        user = request.form.get('username', '').strip().lower()
        pin = request.form.get('pin', '').strip()
        staff = Staff.query.filter(db.func.lower(Staff.username) == user).first()

        if staff and check_password_hash(staff.pin_hash, pin):
            if staff.role == 'ADMIN':
                session['admin_id'] = staff.id
                session['admin_user'] = staff.username
                return redirect(url_for('admin_dashboard'))
            elif staff.role == 'CASHIER':
                session['cashier_id'] = staff.id
                session['cashier_user'] = staff.username
                return redirect(url_for('cashier_terminal'))
        flash('Invalid Username or PIN.', 'error')
    return render_template('staff_login.html', target=target)

@app.route('/staff/logout')
def staff_logout():
    role = request.args.get('role')
    if role == 'admin': session.pop('admin_id', None); session.pop('admin_user', None)
    elif role == 'cashier': session.pop('cashier_id', None); session.pop('cashier_user', None)
    else: session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('staff_login'))

# ==================== INITIAL SEEDER & SAFE AUTO-MIGRATION ====================

with app.app_context():
    db.create_all()

    # Self-healing Schema Inspector that prevents aborted PostgreSQL transactions
    inspector = inspect(db.engine)
    
    cust_cols = [c['name'] for c in inspector.get_columns('customer')]
    if 'last_active_at' not in cust_cols:
        with db.engine.begin() as conn:
            conn.execute(text("ALTER TABLE customer ADD COLUMN last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))

    prod_cols = [c['name'] for c in inspector.get_columns('product')]
    if 'available_start_time' not in prod_cols:
        with db.engine.begin() as conn:
            conn.execute(text("ALTER TABLE product ADD COLUMN available_start_time VARCHAR(10)"))
    if 'available_end_time' not in prod_cols:
        with db.engine.begin() as conn:
            conn.execute(text("ALTER TABLE product ADD COLUMN available_end_time VARCHAR(10)"))

    vault_cols = [c['name'] for c in inspector.get_columns('vault_drop')]
    if 'cash_breakdown' not in vault_cols:
        with db.engine.begin() as conn:
            conn.execute(text("ALTER TABLE vault_drop ADD COLUMN cash_breakdown TEXT"))

    default_roles = [
        ('admin', '1234', 'ADMIN'),
        ('cashier1', '1111', 'CASHIER')
    ]
    for user, pin, role in default_roles:
        st = Staff.query.filter_by(username=user).first()
        if not st:
            db.session.add(Staff(username=user, pin_hash=generate_password_hash(pin), role=role))
        else:
            st.pin_hash = generate_password_hash(pin)
            st.role = role

    db.session.commit()
    ensure_default_promos()

if __name__ == '__main__':
    app.run(debug=True, port=5000)