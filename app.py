import os
import random
import string
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, date, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'macleens-hk-pos-2026')

database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///foodhouse_pos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Permanent sessions for POS stations
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=365)

db = SQLAlchemy(app)

# ==================== EMAIL NOTIFIER ====================

def send_order_email(order_id, total, cust_name, o_type):
    mail_user = os.environ.get('MAIL_USERNAME')
    mail_pass = os.environ.get('MAIL_PASSWORD')
    mail_to = os.environ.get('ORDER_ALERT_EMAIL', mail_user)
    
    if not (mail_user and mail_pass and mail_to):
        return

    try:
        msg = MIMEText(f"New Order #{order_id} received!\nCustomer: {cust_name}\nType: {o_type}\nPayable Total: ₱{total:,.2f}")
        msg['Subject'] = f"🔔 [Macleen's Alert] New Order #{order_id} (₱{total:,.2f})"
        msg['From'] = mail_user
        msg['To'] = mail_to

        server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=5)
        server.login(mail_user, mail_pass)
        server.sendmail(mail_user, [mail_to], msg.as_string())
        server.quit()
    except Exception as e:
        print(f"Email alert error: {e}")

# ==================== MODELS ====================

class Staff(db.Model):
    __tablename__ = 'staff'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    pin_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False) # ADMIN, CASHIER, KITCHEN, RIDER
    plate_number = db.Column(db.String(30), nullable=True)
    active = db.Column(db.Boolean, default=True)

class Customer(db.Model):
    __tablename__ = 'customer'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(30), unique=True, nullable=False)
    fb_messenger = db.Column(db.String(150), nullable=True)
    pin_hash = db.Column(db.String(255), nullable=False)
    profile_image = db.Column(db.Text, nullable=True)
    
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
    accumulated_wifi_mins = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
    is_featured = db.Column(db.Boolean, default=False)
    is_top_seller = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    total_likes = db.Column(db.Integer, default=0)

class ProductLike(db.Model):
    __tablename__ = 'product_like'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id', ondelete='CASCADE'), nullable=False)
    ip_address = db.Column(db.String(50), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id', ondelete='SET NULL'), nullable=True)
    points_awarded = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ProductComment(db.Model):
    __tablename__ = 'product_comment'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id', ondelete='CASCADE'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id', ondelete='SET NULL'), nullable=True)
    author_name = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(50), nullable=False)
    comment_text = db.Column(db.Text, nullable=False)
    points_awarded = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    __tablename__ = 'order'
    id = db.Column(db.Integer, primary_key=True)
    order_type = db.Column(db.String(20), nullable=False) # DINE_IN, PICKUP, DELIVERY, TABLET
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    customer_name = db.Column(db.String(100), default='Walk-in')
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
    payment_method = db.Column(db.String(20), nullable=False) # CASH, GCASH, CREDIT, COD, COP
    payment_verified = db.Column(db.Boolean, default=False)
    
    status = db.Column(db.String(30), default="VERIFICATION")
    assigned_rider = db.Column(db.String(80), nullable=True)
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
    visited_at = db.Column(db.DateTime, default=datetime.utcnow)

# ==================== HELPERS ====================

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or '127.0.0.1'

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'staff_role' not in session or session['staff_role'] not in roles:
                flash("Unauthorized access.", "error")
                return redirect(url_for('staff_login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ==================== STOREFRONT & API ====================

@app.route('/')
def store_catalog():
    ip = get_client_ip()
    if not SiteVisitor.query.filter_by(ip_address=ip).first():
        db.session.add(SiteVisitor(ip_address=ip))
        db.session.commit()
    
    unique_visitors = SiteVisitor.query.count()
    categories = Category.query.all()
    featured = Product.query.filter_by(is_featured=True, is_active=True).all()
    top_sellers = Product.query.filter_by(is_top_seller=True, is_active=True).all()
    products = Product.query.filter_by(is_active=True).order_by(Product.total_likes.desc()).all()
    
    return render_template('store_catalog.html', 
                           categories=categories, 
                           featured=featured, 
                           top_sellers=top_sellers, 
                           products=products, 
                           unique_visitors=unique_visitors)

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
        new_like = ProductLike(product_id=product_id, ip_address=ip, customer_id=cust_id, points_awarded=bool(cust_id))
        prod.total_likes = (prod.total_likes or 0) + 1
        
        if cust_id:
            cust = Customer.query.get(cust_id)
            if cust and not RewardLedger.query.filter_by(customer_id=cust.id, reason=f"Like Product #{product_id}").first():
                cust.points_balance += 2
                db.session.add(RewardLedger(customer_id=cust.id, points_change=2, reason=f"Like Product #{product_id}"))
        
        db.session.add(new_like)
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
    
    name = "Guest (" + ip + ")"
    if cust_id:
        cust = Customer.query.get(cust_id)
        if cust:
            name = cust.name
            if not RewardLedger.query.filter_by(customer_id=cust.id, reason=f"Comment Product #{product_id}").first():
                cust.points_balance += 2
                db.session.add(RewardLedger(customer_id=cust.id, points_change=2, reason=f"Comment Product #{product_id}"))
    
    comment = ProductComment(product_id=product_id, customer_id=cust_id, author_name=name, ip_address=ip, comment_text=text)
    db.session.add(comment)
    db.session.commit()
    return jsonify({'success': True, 'author': name, 'comment': text})

@app.route('/api/storefront-checkout', methods=['POST'])
def api_storefront_checkout():
    data = request.get_json() or {}
    items = data.get('items', [])
    order_type = data.get('order_type', 'PICKUP').upper()
    name = data.get('customer_name', '').strip()
    contact = data.get('contact', '').strip()
    fb = data.get('fb_messenger', '').strip()
    pay_method = data.get('payment_method', 'CASH').upper()
    notes = data.get('notes', '').strip() or 'None'
    gcash_ref = data.get('gcash_ref', '').strip()
    target_time = data.get('target_time', '').strip()

    if not items or not name or not contact:
        return jsonify({'success': False, 'message': 'Please complete your name, mobile, and cart items.'}), 400

    if pay_method in ['GCASH', 'CREDIT'] and not fb:
        return jsonify({'success': False, 'message': 'Facebook account is required for GCash/Credit verification.'}), 400

    if pay_method == 'GCASH' and (len(gcash_ref) < 6):
        return jsonify({'success': False, 'message': 'Please provide the last 6 digits of your GCash Reference Number.'}), 400

    subtotal = sum(Product.query.get(it['product_id']).price * int(it['quantity']) for it in items if Product.query.get(it['product_id']))
    delivery_fee = 30.0 if order_type == 'DELIVERY' else 0.0
    total = subtotal + delivery_fee

    order = Order(
        order_type=order_type,
        customer_name=name,
        contact_number=contact,
        fb_messenger=fb,
        delivery_address=data.get('delivery_address') if order_type == 'DELIVERY' else None,
        landmark=data.get('landmark') if order_type == 'DELIVERY' else None,
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
    send_order_email(order.id, total, name, order_type)
    return jsonify({'success': True, 'order_id': order.id, 'total': total})

# ==================== TABLET & CASHIER TERMINALS ====================

@app.route('/tablet')
def tablet_kiosk():
    session.permanent = True
    categories = Category.query.all()
    products = Product.query.filter_by(is_active=True).order_by(Product.category_name, Product.name).all()
    return render_template('tablet.html', categories=categories, products=products)

@app.route('/pos/cashier')
@role_required('ADMIN', 'CASHIER')
def cashier_terminal():
    session.permanent = True
    categories = Category.query.all()
    products = Product.query.filter_by(is_active=True).all()
    pending_orders = Order.query.filter_by(status="VERIFICATION").order_by(Order.created_at.asc()).all()
    ready_orders = Order.query.filter_by(status="READY").order_by(Order.created_at.asc()).all()
    riders = Staff.query.filter_by(role='RIDER', active=True).all()
    today_wifi_claims = Customer.query.filter_by(last_wifi_claim=date.today()).all()
    return render_template('cashier_pos.html', categories=categories, products=products, 
                           pending_orders=pending_orders, ready_orders=ready_orders, 
                           riders=riders, today_wifi_claims=today_wifi_claims)

@app.route('/pos/verify/<int:order_id>', methods=['POST'])
@role_required('ADMIN', 'CASHIER')
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
        flash(f"Order #{order.id} accepted & sent to Kitchen KDS.", "success")
    else:
        for item in order.items:
            prod = Product.query.get(item.product_id)
            if prod:
                prod.stock += item.quantity
        order.status = "CANCELLED"
        db.session.commit()
        flash(f"Order #{order.id} rejected & stock restored.", "info")

    return redirect(url_for('cashier_terminal'))

@app.route('/pos/complete/<int:order_id>', methods=['POST'])
@role_required('ADMIN', 'CASHIER')
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

# ==================== KITCHEN & RIDER ====================

@app.route('/portal/kitchen')
@role_required('ADMIN', 'KITCHEN')
def kitchen_queue():
    session.permanent = True
    queue = Order.query.filter(Order.status.in_(['KITCHEN_QUEUE', 'PREPARING'])).order_by(Order.created_at.asc()).all()
    return render_template('kitchen_kds.html', queue=queue)

@app.route('/portal/kitchen/status/<int:order_id>', methods=['POST'])
@role_required('ADMIN', 'KITCHEN')
def update_kitchen_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    if new_status in ['PREPARING', 'READY']:
        order.status = new_status
        db.session.commit()
    return redirect(url_for('kitchen_queue'))

@app.route('/portal/rider')
@role_required('ADMIN', 'RIDER')
def rider_portal():
    session.permanent = True
    ready_deliveries = Order.query.filter_by(status="READY", order_type="DELIVERY").all()
    my_deliveries = Order.query.filter_by(status="OUT_FOR_DELIVERY", assigned_rider=session.get('staff_user')).all()
    return render_template('rider_portal.html', ready_deliveries=ready_deliveries, my_deliveries=my_deliveries)

@app.route('/portal/rider/claim/<int:order_id>', methods=['POST'])
@role_required('ADMIN', 'RIDER')
def claim_delivery(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = "OUT_FOR_DELIVERY"
    order.assigned_rider = session.get('staff_user')
    db.session.commit()
    return redirect(url_for('rider_portal'))

@app.route('/portal/rider/complete/<int:order_id>', methods=['POST'])
@role_required('ADMIN', 'RIDER')
def complete_delivery(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = "COMPLETED"
    if order.customer_id and order.payment_method != "CREDIT":
        cust = Customer.query.get(order.customer_id)
        if cust:
            earned = int(order.total_amount // 30)
            if earned > 0:
                cust.points_balance += earned
                db.session.add(RewardLedger(customer_id=cust.id, points_change=earned, reason=f"Delivered Order #{order.id}"))
    db.session.commit()
    return redirect(url_for('rider_portal'))

# ==================== ACCOUNTING & ANALYTICS ====================

@app.route('/portal/accounting')
@role_required('ADMIN')
def accounting_portal():
    session.permanent = True
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

# ==================== MASTER ADMIN ====================

@app.route('/admin')
@role_required('ADMIN')
def admin_dashboard():
    session.permanent = True
    products = Product.query.order_by(Product.total_likes.desc()).all()
    categories = Category.query.all()
    staff_members = Staff.query.all()
    customers = Customer.query.order_by(Customer.id.desc()).all()
    unique_visitors = SiteVisitor.query.count()
    comments = ProductComment.query.order_by(ProductComment.created_at.desc()).limit(15).all()
    
    completed = Order.query.filter_by(status='COMPLETED').all()
    total_rev = sum(o.total_amount for o in completed)
    total_ar = sum((c.outstanding_ar or 0.0) for c in customers)
    
    return render_template('admin.html', products=products, categories=categories, 
                           staff_members=staff_members, customers=customers, 
                           unique_visitors=unique_visitors, comments=comments,
                           total_rev=total_rev, total_ar=total_ar)

@app.route('/admin/change-password', methods=['POST'])
def change_password():
    new_pin = request.form.get('new_pin', '').strip()
    if not new_pin:
        flash("Password / PIN cannot be empty.", "error")
        return redirect(request.referrer or url_for('staff_login'))

    if 'staff_id' in session:
        st = Staff.query.get(session['staff_id'])
        if st:
            st.pin_hash = generate_password_hash(new_pin)
            db.session.commit()
            flash("Staff PIN successfully updated.", "success")
    elif 'customer_id' in session:
        cust = Customer.query.get(session['customer_id'])
        if cust:
            cust.pin_hash = generate_password_hash(new_pin)
            db.session.commit()
            flash("Security PIN updated.", "success")

    return redirect(request.referrer or url_for('store_catalog'))

@app.route('/admin/batch-update-products', methods=['POST'])
@role_required('ADMIN')
def admin_batch_update_products():
    for pid in request.form.getlist('product_id'):
        prod = Product.query.get(pid)
        if prod:
            prod.price = float(request.form.get(f'price_{pid}') or prod.price)
            prod.cost = float(request.form.get(f'cost_{pid}') or prod.cost)
            prod.stock = int(request.form.get(f'stock_{pid}') or prod.stock)
            prod.is_active = (f'is_active_{pid}' in request.form)
            prod.is_featured = (f'is_featured_{pid}' in request.form)
            prod.is_top_seller = (f'is_top_seller_{pid}' in request.form)
    db.session.commit()
    flash("Bulk product catalog updated.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add-rider', methods=['POST'])
@role_required('ADMIN')
def admin_add_rider():
    user = request.form.get('username', '').strip()
    pin = request.form.get('pin', '').strip()
    plate = request.form.get('plate_number', '').strip()
    
    if Staff.query.filter_by(username=user).first():
        flash("Username exists.", "error")
    else:
        db.session.add(Staff(username=user, pin_hash=generate_password_hash(pin), role='RIDER', plate_number=plate))
        db.session.commit()
        flash(f"Rider {user} created.", "success")
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
        flash("Invalid Credentials.", "error")
    return render_template('customer_login.html')

@app.route('/portal/register', methods=['GET', 'POST'])
def customer_register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        contact = request.form.get('contact', '').strip()
        messenger = request.form.get('fb_messenger', '').strip()
        pin = request.form.get('pin', '').strip()

        if Customer.query.filter_by(contact=contact).first():
            flash("Contact number registered.", "error")
            return redirect(url_for('customer_register'))

        new_cust = Customer(
            name=name, contact=contact, fb_messenger=messenger, pin_hash=generate_password_hash(pin),
            card_number=f"MFH-{random.randint(1, 100):04d}", card_expires_at=date.today() + timedelta(days=365)
        )
        db.session.add(new_cust)
        db.session.commit()
        session['customer_id'] = new_cust.id
        return redirect(url_for('customer_dashboard'))
    return render_template('customer_register.html')

@app.route('/portal/dashboard')
def customer_dashboard():
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    cust = Customer.query.get(session['customer_id'])
    orders = Order.query.filter_by(customer_id=cust.id).order_by(Order.created_at.desc()).limit(10).all()
    return render_template('customer_dashboard.html', cust=cust, orders=orders)

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
        cust.accumulated_wifi_mins = (cust.accumulated_wifi_mins or 0) + 10
        db.session.commit()
        flash(f"Claimed 10-Mins Free Wi-Fi! Passcode: {voucher}", "success")
    return redirect(url_for('customer_dashboard'))

@app.route('/staff/login', methods=['GET', 'POST'])
def staff_login():
    if request.method == 'POST':
        user = request.form.get('username')
        pin = request.form.get('pin')
        staff = Staff.query.filter_by(username=user).first()
        if staff and check_password_hash(staff.pin_hash, pin):
            session.permanent = True
            session['staff_id'] = staff.id
            session['staff_user'] = staff.username
            session['staff_role'] = staff.role
            
            if staff.role == 'ADMIN': return redirect(url_for('admin_dashboard'))
            if staff.role == 'CASHIER': return redirect(url_for('cashier_terminal'))
            if staff.role == 'KITCHEN': return redirect(url_for('kitchen_queue'))
            if staff.role == 'RIDER': return redirect(url_for('rider_portal'))
        flash('Invalid Credentials.', 'error')
    return render_template('staff_login.html')

@app.route('/staff/logout')
def staff_logout():
    session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('staff_login'))

# ==================== SEEDER ====================

with app.app_context():
    db.create_all()
    default_roles = [
        ('admin', '1234', 'ADMIN', None),
        ('cashier1', '1111', 'CASHIER', None),
        ('kitchen1', '2222', 'KITCHEN', None),
        ('rider1', '3333', 'RIDER', 'MFH-01')
    ]
    for user, pin, role, plate in default_roles:
        if not Staff.query.filter_by(username=user).first():
            db.session.add(Staff(username=user, pin_hash=generate_password_hash(pin), role=role, plate_number=plate))
    
    # Ensure Wi-Fi 5 Pesos Product Exists
    if not Product.query.filter_by(name="Wi-Fi Voucher 30 Mins").first():
        db.session.add(Product(name="Wi-Fi Voucher 30 Mins", category_name="Services", price=5.0, cost=0.0, stock=999, is_active=True))
        if not Category.query.filter_by(name="Services").first():
            db.session.add(Category(name="Services"))
        db.session.commit()

    db.session.commit()

if __name__ == '__main__':
    app.run(debug=True, port=5000)