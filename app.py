import os
import random
import string
from datetime import datetime, date, timedelta, time
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
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
    plate_number = db.Column(db.String(30), nullable=True)
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
    assigned_rider = db.Column(db.String(80), nullable=True)
    rider_delivered = db.Column(db.Boolean, default=False)
    customer_delivered = db.Column(db.Boolean, default=False)
    cashier_delivered = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, nullable=False, default="None")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    customer = db.relationship('Customer', backref='orders', lazy=True)
    items = db.relationship('OrderItem', backref='order_rel', cascade="all, delete-orphan", lazy=True)

class OrderItem(db.Model):
    __tablename__ = 'order_item'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
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
        'store_close_time': '19:00',
        'delivery_open_time': '09:00',
        'delivery_close_time': '17:00',
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
    store_close = parse_t(s.get('store_close_time', '19:00'), time(19, 0))
    del_open = parse_t(s.get('delivery_open_time', '09:00'), time(9, 0))
    del_close = parse_t(s.get('delivery_close_time', '17:00'), time(17, 0))

    is_store_active = (s.get('is_store_open') == 'true') and (store_open <= now_ph <= store_close)
    is_delivery_active = (s.get('is_delivery_enabled') == 'true') and (del_open <= now_ph <= del_close) and is_store_active

    return {
        'store_open': is_store_active,
        'delivery_open': is_delivery_active,
        'settings': s,
        'current_time': now_ph.strftime('%I:%M %p')
    }

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

def require_kitchen(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not (session.get('kitchen_user') or session.get('admin_user')):
            return redirect(url_for('staff_login', target='kitchen'))
        return f(*args, **kwargs)
    return decorated

def require_rider(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not (session.get('rider_user') or session.get('admin_user')):
            return redirect(url_for('staff_login', target='rider'))
        return f(*args, **kwargs)
    return decorated

# ==================== REAL-TIME POLLING API ====================

@app.route('/api/queue-counts')
def api_queue_counts():
    pending_cashier = Order.query.filter_by(status="VERIFICATION").count()
    pending_kitchen = Order.query.filter(Order.status.in_(['KITCHEN_QUEUE', 'PREPARING'])).count()
    return jsonify({
        'pending_cashier': pending_cashier,
        'pending_kitchen': pending_kitchen
    })

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

    unique_visitors = SiteVisitor.query.count()
    total_accumulated_visits = db.session.query(db.func.coalesce(db.func.sum(SiteVisitor.visit_count), 0)).scalar() or unique_visitors

    categories = Category.query.all()
    featured = Product.query.filter_by(is_featured=True, is_active=True).all()
    top_sellers = Product.query.filter_by(is_top_seller=True, is_active=True).all()
    products = Product.query.filter_by(is_active=True).order_by(Product.total_likes.desc(), Product.id.asc()).all()

    liked_ids = {pl.product_id for pl in ProductLike.query.filter_by(ip_address=get_client_ip()).all()}
    delivery_zones = DeliveryZone.query.filter_by(is_active=True).all()
    status = check_operating_status()

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
                           cust=cust,
                           status=status,
                           unique_visitors=unique_visitors, 
                           total_accumulated_visits=total_accumulated_visits)

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
    landmark = data.get('landmark', '').strip()
    delivery_address = data.get('delivery_address', '').strip()
    zone_id = data.get('delivery_zone_id')
    gcash_ref = data.get('gcash_ref', '').strip()
    fb = data.get('fb_messenger', '').strip()

    if order_type == 'PICKUP' and not status['store_open']:
        return jsonify({'success': False, 'message': 'Store ordering is currently closed.'}), 400

    if order_type == 'DELIVERY' and not status['delivery_open']:
        return jsonify({'success': False, 'message': 'Barangay delivery is currently unavailable/closed.'}), 400

    if not items or not target_time:
        return jsonify({'success': False, 'message': 'Please complete your target time and select cart items.'}), 400

    if order_type == 'DELIVERY':
        if not landmark or not delivery_address:
            return jsonify({'success': False, 'message': 'Delivery address and Landmark are strictly required.'}), 400

    if pay_method == 'CREDIT' and not cust.is_credit_eligible:
        return jsonify({'success': False, 'message': 'Your account is not authorized for A/R Credit.'}), 403

    if pay_method in ['GCASH', 'CREDIT'] and not fb:
        return jsonify({'success': False, 'message': 'Facebook messenger link is required for evaluation.'}), 400

    if pay_method == 'GCASH' and len(gcash_ref) < 6:
        return jsonify({'success': False, 'message': 'Please input the 6-digit GCash Reference Number.'}), 400

    subtotal = sum(Product.query.get(it['product_id']).price * int(it['quantity']) for it in items if Product.query.get(it['product_id']))

    delivery_fee = 0.0
    if order_type == 'DELIVERY':
        zone = DeliveryZone.query.get(zone_id) if zone_id else None
        delivery_fee = zone.rate if zone else 40.0
        cust.default_address = delivery_address
        cust.default_landmark = landmark
        cust.fb_messenger = fb

    total = subtotal + delivery_fee

    order = Order(
        order_type=order_type,
        customer_id=cust.id,
        customer_name=cust.name,
        contact_number=cust.contact,
        fb_messenger=fb,
        delivery_address=delivery_address if order_type == 'DELIVERY' else None,
        landmark=landmark if order_type == 'DELIVERY' else None,
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

# ==================== OPERATING HOURS & AUTH ENDPOINTS ====================

@app.route('/admin/settings/hours', methods=['POST'])
def update_store_hours():
    if not (session.get('admin_user') or session.get('cashier_user')):
        flash("Unauthorized", "error")
        return redirect(request.referrer or url_for('store_catalog'))

    keys = ['store_open_time', 'store_close_time', 'delivery_open_time', 'delivery_close_time']
    for k in keys:
        if k in request.form:
            s = StoreSetting.query.filter_by(key=k).first()
            if not s:
                db.session.add(StoreSetting(key=k, value=request.form[k]))
            else:
                s.value = request.form[k]

    for toggle in ['is_store_open', 'is_delivery_enabled']:
        val = 'true' if request.form.get(toggle) == 'on' else 'false'
        s = StoreSetting.query.filter_by(key=toggle).first()
        if not s:
            db.session.add(StoreSetting(key=toggle, value=val))
        else:
            s.value = val

    db.session.commit()
    flash("Operating schedule updated successfully!", "success")
    return redirect(request.referrer or url_for('store_catalog'))

@app.route('/auth/change-password', methods=['POST'])
def change_staff_password():
    staff_user = session.get('admin_user') or session.get('cashier_user') or session.get('kitchen_user') or session.get('rider_user')
    if not staff_user:
        flash("Please log in first.", "error")
        return redirect(url_for('staff_login'))

    staff = Staff.query.filter_by(username=staff_user).first()
    old_p = request.form.get('old_password', '').strip()
    new_p = request.form.get('new_password', '').strip()
    conf_p = request.form.get('confirm_password', '').strip()

    if not staff or not check_password_hash(staff.pin_hash, old_p):
        flash("Current password / PIN is incorrect.", "error")
        return redirect(request.referrer or url_for('store_catalog'))

    if len(new_p) < 4:
        flash("New password must be at least 4 characters.", "error")
        return redirect(request.referrer or url_for('store_catalog'))

    if new_p != conf_p:
        flash("New passwords do not match.", "error")
        return redirect(request.referrer or url_for('store_catalog'))

    staff.pin_hash = generate_password_hash(new_p)
    db.session.commit()
    flash("Staff password successfully changed!", "success")
    return redirect(request.referrer or url_for('store_catalog'))

@app.route('/auth/change-staff-password', methods=['POST'])
@require_cashier
def change_specific_staff_password():
    target_username = request.form.get('target_username', '').strip()
    admin_pin = request.form.get('admin_pin', '').strip()
    new_pin = request.form.get('new_pin', '').strip()

    staff = Staff.query.filter_by(username=target_username).first()
    if not staff:
        flash("Staff user not found.", "error")
        return redirect(url_for('cashier_terminal'))

    current_user = session.get('admin_user') or session.get('cashier_user')
    auth_staff = Staff.query.filter_by(username=current_user).first()

    if not auth_staff or not check_password_hash(auth_staff.pin_hash, admin_pin):
        flash("Authorization failed: Your current password/PIN is incorrect.", "error")
        return redirect(url_for('cashier_terminal'))

    if len(new_pin) < 4:
        flash("New PIN/Password must be at least 4 characters.", "error")
        return redirect(url_for('cashier_terminal'))

    staff.pin_hash = generate_password_hash(new_pin)
    db.session.commit()
    flash(f"Successfully updated PIN for [{staff.username.upper()}] ({staff.role})!", "success")
    return redirect(url_for('cashier_terminal'))

@app.route('/portal/change-pin', methods=['POST'])
def change_customer_pin():
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))

    cust = Customer.query.get(session['customer_id'])
    old_pin = request.form.get('old_pin', '').strip()
    new_pin = request.form.get('new_pin', '').strip()

    if not check_password_hash(cust.pin_hash, old_pin):
        flash("Current PIN is incorrect.", "error")
        return redirect(url_for('customer_dashboard'))

    if len(new_pin) != 4 or not new_pin.isdigit():
        flash("New PIN must be exactly 4 digits.", "error")
        return redirect(url_for('customer_dashboard'))

    cust.pin_hash = generate_password_hash(new_pin)
    db.session.commit()
    flash("Your 4-digit security PIN has been updated!", "success")
    return redirect(url_for('customer_dashboard'))

# ==================== CASHIER TERMINAL ====================

@app.route('/pos/cashier')
@require_cashier
def cashier_terminal():
    categories = Category.query.all()
    products = Product.query.filter_by(is_active=True).all()
    pending_orders = Order.query.filter_by(status="VERIFICATION").order_by(Order.created_at.asc()).all()
    ready_orders = Order.query.filter_by(status="READY").order_by(Order.created_at.asc()).all()
    out_for_delivery = Order.query.filter_by(status="OUT_FOR_DELIVERY").order_by(Order.created_at.asc()).all()
    riders = Staff.query.filter_by(role='RIDER', active=True).all()
    today_wifi_claims = Customer.query.filter_by(last_wifi_claim=date.today()).all()
    staff_list = Staff.query.all()

    today = date.today()
    today_expenses = Expense.query.filter(db.func.date(Expense.created_at) == today).order_by(Expense.created_at.desc()).all()
    today_drops = VaultDrop.query.filter(db.func.date(VaultDrop.created_at) == today).order_by(VaultDrop.drop_number.asc()).all()
    next_drop_num = len(today_drops) + 1

    return render_template('cashier_pos.html', 
                           categories=categories, 
                           products=products, 
                           pending_orders=pending_orders, 
                           ready_orders=ready_orders, 
                           out_for_delivery=out_for_delivery, 
                           riders=riders, 
                           today_wifi_claims=today_wifi_claims,
                           staff_list=staff_list,
                           today_expenses=today_expenses,
                           today_drops=today_drops,
                           next_drop_num=next_drop_num)

@app.route('/pos/misc-sale', methods=['POST'])
@require_cashier
def cashier_misc_sale():
    service_name = request.form.get('service_name', '').strip() or 'Printing / Custom Service'
    amount = float(request.form.get('amount') or 0.0)
    pay_method = request.form.get('payment_method', 'CASH')
    notes = request.form.get('notes', '').strip() or 'Over-the-counter Misc Service'

    if amount <= 0:
        flash("Amount must be greater than zero.", "error")
        return redirect(url_for('cashier_terminal'))

    order = Order(
        order_type='DINE-IN/WALKIN',
        customer_name='Walk-in Customer',
        contact_number='N/A',
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
        product_id=0,
        product_name=f"[Service] {service_name}",
        unit_price=amount,
        cost_price=0.0,
        quantity=1,
        subtotal=amount
    ))

    db.session.commit()
    flash(f"Misc Sale recorded: {service_name} (₱{amount:,.2f})", "success")
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
    staff_user = session.get('cashier_user') or session.get('admin_user') or 'Cashier'

    if amount <= 0:
        flash("Drop amount must be greater than zero.", "error")
        return redirect(url_for('cashier_terminal'))

    db.session.add(VaultDrop(drop_number=drop_num, amount=amount, notes=notes, created_by=staff_user))
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
        rider = request.form.get('assigned_rider')
        if rider:
            order.assigned_rider = rider
        order.status = "KITCHEN_QUEUE"
        db.session.commit()
        flash(f"Order #{order.id} verified & sent to Kitchen.", "success")
    else:
        for item in order.items:
            prod = Product.query.get(item.product_id)
            if prod:
                prod.stock += item.quantity
        order.status = "CANCELLED"
        db.session.commit()
        flash(f"Order #{order.id} cancelled.", "info")

    return redirect(url_for('cashier_terminal'))

@app.route('/pos/confirm-delivery/<int:order_id>', methods=['POST'])
@require_cashier
def cashier_confirm_delivery(order_id):
    order = Order.query.get_or_404(order_id)
    order.cashier_delivered = True

    if order.rider_delivered and (order.customer_delivered or order.cashier_delivered):
        order.status = "COMPLETED"
        if order.customer_id and order.payment_method != "CREDIT":
            cust = Customer.query.get(order.customer_id)
            if cust:
                cust.accumulated_spend += order.total_amount
                earned = int(order.total_amount // 30)
                if earned > 0:
                    cust.points_balance += earned
                    db.session.add(RewardLedger(customer_id=cust.id, points_change=earned, reason=f"Purchase Order #{order.id}"))
    db.session.commit()
    flash(f"Order #{order.id} delivery verified by Cashier.", "success")
    return redirect(url_for('cashier_terminal'))

@app.route('/pos/complete/<int:order_id>', methods=['POST'])
@require_cashier
def complete_order(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = "COMPLETED"

    if order.customer_id and order.payment_method != "CREDIT":
        cust = Customer.query.get(order.customer_id)
        if cust:
            cust.accumulated_spend += order.total_amount
            earned = int(order.total_amount // 30)
            if earned > 0:
                cust.points_balance += earned
                db.session.add(RewardLedger(customer_id=cust.id, points_change=earned, reason=f"Purchase Order #{order.id}"))

    db.session.commit()
    flash(f"Order #{order.id} completed & archived.", "success")
    return redirect(url_for('cashier_terminal'))

# ==================== KITCHEN QUEUE ====================

@app.route('/portal/kitchen')
@require_kitchen
def kitchen_queue():
    queue = Order.query.filter(Order.status.in_(['KITCHEN_QUEUE', 'PREPARING'])).order_by(Order.created_at.asc()).all()
    return render_template('kitchen_kds.html', queue=queue)

@app.route('/portal/kitchen/status/<int:order_id>', methods=['POST'])
@require_kitchen
def update_kitchen_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    if new_status in ['PREPARING', 'READY']:
        order.status = new_status
        db.session.commit()
    return redirect(url_for('kitchen_queue'))

# ==================== RIDER HUB ====================

@app.route('/portal/rider')
@require_rider
def rider_portal():
    current_rider = session.get('rider_user')
    pending_active_deliveries = Order.query.filter(
        Order.assigned_rider == current_rider,
        Order.status == 'OUT_FOR_DELIVERY'
    ).count()

    can_accept_more = (pending_active_deliveries == 0)
    ready_deliveries = Order.query.filter_by(status="READY", order_type="DELIVERY").all()
    my_deliveries = Order.query.filter_by(status="OUT_FOR_DELIVERY", assigned_rider=current_rider).all()

    return render_template('rider_portal.html', 
                           ready_deliveries=ready_deliveries, 
                           my_deliveries=my_deliveries,
                           can_accept_more=can_accept_more,
                           pending_active_deliveries=pending_active_deliveries)

@app.route('/portal/rider/claim-batch', methods=['POST'])
@require_rider
def rider_claim_batch():
    current_rider = session.get('rider_user')
    order_ids = request.form.getlist('order_ids')
    for oid in order_ids:
        order = Order.query.get(oid)
        if order and order.status == 'READY':
            order.status = "OUT_FOR_DELIVERY"
            order.assigned_rider = current_rider
    db.session.commit()
    flash(f"Claimed {len(order_ids)} orders for dispatch!", "success")
    return redirect(url_for('rider_portal'))

@app.route('/portal/rider/mark-delivered/<int:order_id>', methods=['POST'])
@require_rider
def rider_mark_delivered(order_id):
    order = Order.query.get_or_404(order_id)
    order.rider_delivered = True

    if order.rider_delivered and (order.customer_delivered or order.cashier_delivered):
        order.status = "COMPLETED"
        if order.customer_id and order.payment_method != "CREDIT":
            cust = Customer.query.get(order.customer_id)
            if cust:
                cust.accumulated_spend += order.total_amount
                earned = int(order.total_amount // 30)
                if earned > 0:
                    cust.points_balance += earned
                    db.session.add(RewardLedger(customer_id=cust.id, points_change=earned, reason=f"Purchase Order #{order.id}"))

    db.session.commit()
    flash(f"Order #{order.id} confirmed by Rider. Awaiting customer confirmation.", "info")
    return redirect(url_for('rider_portal'))

# ==================== TABLET KIOSK ====================

@app.route('/tablet')
def tablet_kiosk():
    categories = Category.query.all()
    products = Product.query.filter_by(is_active=True).order_by(Product.category_name, Product.name).all()
    return render_template('tablet.html', categories=categories, products=products)

# ==================== MASTER ADMIN & SETTINGS ====================

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

    unique_visitors = SiteVisitor.query.count()
    total_accumulated_visits = db.session.query(db.func.coalesce(db.func.sum(SiteVisitor.visit_count), 0)).scalar() or unique_visitors

    completed = Order.query.filter_by(status='COMPLETED').all()
    total_rev = sum(o.total_amount for o in completed)
    total_cost = sum(sum(it.cost_price * it.quantity for it in o.items) for o in completed)
    estimated_profit = total_rev - total_cost
    total_ar = sum((c.outstanding_ar or 0.0) for c in customers)

    return render_template('admin.html', 
                           products=products, 
                           categories=categories, 
                           staff_members=staff_members, 
                           customers=customers, 
                           delivery_zones=delivery_zones,
                           unique_visitors=unique_visitors, 
                           total_accumulated_visits=total_accumulated_visits,
                           total_rev=total_rev,
                           total_cost=total_cost,
                           estimated_profit=estimated_profit,
                           total_ar=total_ar,
                           current_sort=sort_by)

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
    today = date.today()
    week_ago = datetime.utcnow() - timedelta(days=7)
    month_ago = datetime.utcnow() - timedelta(days=30)

    daily_orders = Order.query.filter(db.func.date(Order.created_at) == today, Order.status == 'COMPLETED').all()
    weekly_orders = Order.query.filter(Order.created_at >= week_ago, Order.status == 'COMPLETED').all()
    monthly_orders = Order.query.filter(Order.created_at >= month_ago, Order.status == 'COMPLETED').all()

    def calc_fin(orders):
        rev = sum(o.total_amount for o in orders)
        cost = sum(sum(it.cost_price * it.quantity for it in o.items) for o in orders)
        return rev, cost, rev - cost

    d_rev, d_cost, d_profit = calc_fin(daily_orders)
    w_rev, w_cost, w_profit = calc_fin(weekly_orders)
    m_rev, m_cost, m_profit = calc_fin(monthly_orders)

    return render_template('accounting.html', 
                           daily_orders=daily_orders,
                           d_rev=d_rev, d_cost=d_cost, d_profit=d_profit,
                           w_rev=w_rev, w_cost=w_cost, w_profit=w_profit,
                           m_rev=m_rev, m_cost=m_cost, m_profit=m_profit)

@app.route('/admin/add-product', methods=['POST'])
@require_admin
def admin_add_product():
    name = request.form.get('name')
    category_name = request.form.get('category_name')
    price = float(request.form.get('price') or 0.0)
    cost = float(request.form.get('cost') or 0.0)
    stock = int(request.form.get('stock') or 100)
    image_url = request.form.get('image_url', '').strip()
    is_featured = bool(request.form.get('is_featured'))
    is_top_seller = bool(request.form.get('is_top_seller'))

    db.session.add(Product(name=name, category_name=category_name, price=price, cost=cost, stock=stock, 
                           image_url=image_url, is_featured=is_featured, is_top_seller=is_top_seller))
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

# ==================== CUSTOMER PORTAL ====================

@app.route('/portal/login', methods=['GET', 'POST'])
def customer_login():
    if request.method == 'POST':
        contact = request.form.get('contact', '').strip()
        pin = request.form.get('pin', '').strip()
        cust = Customer.query.filter_by(contact=contact).first()
        if cust and check_password_hash(cust.pin_hash, pin):
            session['customer_id'] = cust.id
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
            card_expires_at=date.today() + timedelta(days=365)
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
    
    cust = Customer.query.get(session['customer_id'])
    if not cust:
        session.pop('customer_id', None)
        flash("Account session expired. Please log in again.", "info")
        return redirect(url_for('customer_login'))
    
    my_orders = Order.query.filter_by(customer_id=cust.id).order_by(Order.created_at.desc()).all()
    return render_template('customer_dashboard.html', cust=cust, orders=my_orders, today=date.today())

@app.route('/portal/confirm-received/<int:order_id>', methods=['POST'])
def customer_confirm_received(order_id):
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    order = Order.query.get_or_404(order_id)
    if order.customer_id != session['customer_id']:
        return "Unauthorized", 403

    order.customer_delivered = True
    if order.rider_delivered and (order.customer_delivered or order.cashier_delivered):
        order.status = "COMPLETED"
        cust = Customer.query.get(order.customer_id)
        if cust and order.payment_method != "CREDIT":
            cust.accumulated_spend += order.total_amount
            earned = int(order.total_amount // 30)
            if earned > 0:
                cust.points_balance += earned
                db.session.add(RewardLedger(customer_id=cust.id, points_change=earned, reason=f"Purchase Order #{order.id}"))

    db.session.commit()
    flash(f"Order #{order.id} confirmed as received! Thank you!", "success")
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
            elif staff.role == 'KITCHEN':
                session['kitchen_id'] = staff.id
                session['kitchen_user'] = staff.username
                return redirect(url_for('kitchen_queue'))
            elif staff.role == 'RIDER':
                session['rider_id'] = staff.id
                session['rider_user'] = staff.username
                return redirect(url_for('rider_portal'))
        flash('Invalid Username or PIN.', 'error')
    return render_template('staff_login.html', target=target)

@app.route('/staff/logout')
def staff_logout():
    role = request.args.get('role')
    if role == 'admin': session.pop('admin_id', None); session.pop('admin_user', None)
    elif role == 'cashier': session.pop('cashier_id', None); session.pop('cashier_user', None)
    elif role == 'kitchen': session.pop('kitchen_id', None); session.pop('kitchen_user', None)
    elif role == 'rider': session.pop('rider_id', None); session.pop('rider_user', None)
    else: session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('staff_login'))

# ==================== INITIAL SEEDER ====================

with app.app_context():
    db.create_all()
    default_roles = [
        ('admin', '1234', 'ADMIN', None),
        ('cashier1', '1111', 'CASHIER', None),
        ('kitchen1', '2222', 'KITCHEN', None),
        ('rider1', '3333', 'RIDER', 'MFH-01')
    ]
    for user, pin, role, plate in default_roles:
        st = Staff.query.filter_by(username=user).first()
        if not st:
            db.session.add(Staff(username=user, pin_hash=generate_password_hash(pin), role=role, plate_number=plate))
        else:
            st.pin_hash = generate_password_hash(pin)
            st.role = role

    db.session.commit()

if __name__ == '__main__':
    app.run(debug=True, port=5000)