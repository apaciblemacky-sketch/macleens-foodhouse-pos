import os
import random
from datetime import datetime, date, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'macleens-pos-secret-2026')

database_url = os.environ.get('DATABASE_URL')
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///foodhouse_pos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=6)

db = SQLAlchemy(app)

# ==================== DATA MODELS ====================

class Staff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    pin_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # ADMIN, CASHIER, KITCHEN, RIDER, INVESTOR
    active = db.Column(db.Boolean, default=True)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(30), unique=True, nullable=False)
    fb_messenger = db.Column(db.String(120), nullable=True)
    pin_hash = db.Column(db.String(255), nullable=False)
    
    # Financials & Loyalty
    points_balance = db.Column(db.Float, default=0.0)
    wallet_balance = db.Column(db.Float, default=0.0)
    is_credit_eligible = db.Column(db.Boolean, default=False)
    credit_limit = db.Column(db.Float, default=0.0)
    outstanding_ar = db.Column(db.Float, default=0.0)
    accumulated_spend = db.Column(db.Float, default=0.0)
    
    # Wi-Fi & Cards
    last_wifi_claim = db.Column(db.Date, nullable=True)
    card_number = db.Column(db.String(20), unique=True, nullable=True)
    card_status = db.Column(db.String(20), default="UNREGISTERED")  # UNREGISTERED, ACTIVE, EXPIRED, LOCKED
    card_expires_at = db.Column(db.Date, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    image_url = db.Column(db.String(255), default="https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=500")

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category_name = db.Column(db.String(80), nullable=False)
    price = db.Column(db.Float, nullable=False)
    cost = db.Column(db.Float, default=0.0)
    stock = db.Column(db.Integer, default=50)
    is_ulam = db.Column(db.Boolean, default=False)  # Flag for Ulam voting
    is_featured = db.Column(db.Boolean, default=False)
    is_top_seller = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    image_url = db.Column(db.String(255), default="https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=500")

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_type = db.Column(db.String(20), nullable=False)  # PICKUP, DELIVERY, DINE_IN, TABLET
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    customer_name = db.Column(db.String(100), nullable=False)
    contact_number = db.Column(db.String(50), nullable=False)
    delivery_address = db.Column(db.Text, nullable=True)
    
    # Financial Calculations
    subtotal = db.Column(db.Float, nullable=False)
    delivery_fee = db.Column(db.Float, default=0.0)
    discount_points_used = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)  # CASH, GCASH, CREDIT, COD, COP
    payment_verified = db.Column(db.Boolean, default=False)
    
    # Workflow Status
    status = db.Column(db.String(30), default="VERIFICATION") 
    # Workflow: VERIFICATION -> KITCHEN_QUEUE -> PREPARING -> READY -> OUT_FOR_DELIVERY -> COMPLETED / CANCELLED
    
    assigned_rider = db.Column(db.String(80), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    items = db.relationship('OrderItem', backref='order_rel', cascade="all, delete-orphan", lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product_name = db.Column(db.String(120), nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    item_notes = db.Column(db.String(200), nullable=True)

class UlamVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    vote_date = db.Column(db.Date, default=date.today)
    points_awarded = db.Column(db.Boolean, default=False)

class RewardLedger(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    points_change = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(150), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SiteMetric(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    store_open = db.Column(db.Boolean, default=True)
    visitor_count = db.Column(db.Integer, default=0)

# ==================== AUTH DECORATORS ====================

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

def customer_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'customer_id' not in session:
            return redirect(url_for('customer_login'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== PUBLIC & CUSTOMER PORTALS ====================

@app.route('/')
def store_catalog():
    metric = SiteMetric.query.first()
    if metric:
        metric.visitor_count += 1
        db.session.commit()
    
    products = Product.query.filter_by(is_active=True).all()
    categories = Category.query.all()
    top_sellers = Product.query.filter_by(is_top_seller=True, is_active=True).all()
    featured = Product.query.filter_by(is_featured=True, is_active=True).all()
    
    return render_template(
        'store_catalog.html',
        products=products,
        categories=categories,
        top_sellers=top_sellers,
        featured=featured,
        metric=metric
    )

@app.route('/portal/register', methods=['GET', 'POST'])
def customer_register():
    if request.method == 'POST':
        name = request.form.get('name').strip()
        contact = request.form.get('contact').strip()
        messenger = request.form.get('fb_messenger', '').strip()
        pin = request.form.get('pin').strip()

        if Customer.query.filter_by(contact=contact).first():
            flash("Contact number already registered.", "error")
            return redirect(url_for('customer_register'))

        # Assign Physical Card Number
        card_num = f"MFH-{random.randint(1, 1000):04d}"
        new_cust = Customer(
            name=name,
            contact=contact,
            fb_messenger=messenger,
            pin_hash=generate_password_hash(pin),
            card_number=card_num,
            card_status="ACTIVE",
            card_expires_at=date.today() + timedelta(days=365)
        )
        db.session.add(new_cust)
        db.session.commit()
        session['customer_id'] = new_cust.id
        return redirect(url_for('customer_dashboard'))
    return render_template('customer_register.html')

@app.route('/portal/login', methods=['GET', 'POST'])
def customer_login():
    if request.method == 'POST':
        contact = request.form.get('contact').strip()
        pin = request.form.get('pin').strip()
        cust = Customer.query.filter_by(contact=contact).first()
        if cust and check_password_hash(cust.pin_hash, pin):
            session['customer_id'] = cust.id
            return redirect(url_for('customer_dashboard'))
        flash("Invalid Contact or PIN.", "error")
    return render_template('customer_login.html')

@app.route('/portal/dashboard')
@customer_login_required
def customer_dashboard():
    cust = Customer.query.get(session['customer_id'])
    orders = Order.query.filter_by(customer_id=cust.id).order_by(Order.created_at.desc()).limit(10).all()
    ulam_products = Product.query.filter_by(is_ulam=True, is_active=True).all()
    today_vote = UlamVote.query.filter_by(customer_id=cust.id, vote_date=date.today()).first()
    return render_template('customer_dashboard.html', cust=cust, orders=orders, ulam_products=ulam_products, today_vote=today_vote)

@app.route('/portal/claim-wifi', methods=['POST'])
@customer_login_required
def claim_daily_wifi():
    cust = Customer.query.get(session['customer_id'])
    if cust.last_wifi_claim == date.today():
        flash("Daily 10-minute Free Wi-Fi already claimed today!", "info")
    else:
        cust.last_wifi_claim = date.today()
        db.session.commit()
        flash("Daily 10 Mins Free Wi-Fi activated! Passcode given at cashier.", "success")
    return redirect(url_for('customer_dashboard'))

@app.route('/portal/vote-ulam', methods=['POST'])
@customer_login_required
def vote_ulam():
    cust = Customer.query.get(session['customer_id'])
    prod_id = int(request.form.get('product_id'))
    existing_vote = UlamVote.query.filter_by(customer_id=cust.id, vote_date=date.today()).first()

    if existing_vote:
        existing_vote.product_id = prod_id
        db.session.commit()
        flash("Your Ulam vote was updated (No additional points).", "info")
    else:
        # First vote grants +3 Rewards points
        new_vote = UlamVote(customer_id=cust.id, product_id=prod_id, points_awarded=True)
        cust.points_balance += 3
        ledger = RewardLedger(customer_id=cust.id, points_change=3, reason="Daily Ulam Vote Reward")
        db.session.add_all([new_vote, ledger])
        db.session.commit()
        flash("Vote cast! +3 Rewards Points added to your account!", "success")

    return redirect(url_for('customer_dashboard'))

# ==================== CASHIER & POS PORTAL ====================

@app.route('/pos/cashier', methods=['GET', 'POST'])
@role_required('ADMIN', 'CASHIER')
def cashier_terminal():
    categories = Category.query.all()
    products = Product.query.filter_by(is_active=True).all()
    pending_verification = Order.query.filter_by(status="VERIFICATION").order_by(Order.created_at.asc()).all()
    ready_orders = Order.query.filter_by(status="READY").order_by(Order.created_at.asc()).all()
    return render_template('cashier_pos.html', categories=categories, products=products, pending_verification=pending_verification, ready_orders=ready_orders)

@app.route('/pos/verify-order/<int:order_id>', methods=['POST'])
@role_required('ADMIN', 'CASHIER')
def verify_order(order_id):
    order = Order.query.get_or_404(order_id)
    action = request.form.get('action') # ACCEPT, REJECT

    if action == 'ACCEPT':
        # Verify and Reserve Stock
        for item in order.items:
            prod = Product.query.get(item.product_id)
            if prod and prod.stock < item.quantity:
                flash(f"Insufficient stock for {prod.name} (Only {prod.stock} left).", "error")
                return redirect(url_for('cashier_terminal'))
            if prod:
                prod.stock -= item.quantity
        
        order.payment_verified = True
        order.status = "KITCHEN_QUEUE"
        db.session.commit()
        flash(f"Order #{order.id} sent to Kitchen KDS Queue.", "success")
    else:
        order.status = "CANCELLED"
        db.session.commit()
        flash(f"Order #{order.id} marked UNAVAILABLE / Cancelled.", "info")

    return redirect(url_for('cashier_terminal'))

@app.route('/pos/complete-pickup/<int:order_id>', methods=['POST'])
@role_required('ADMIN', 'CASHIER')
def complete_pickup(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = "COMPLETED"
    
    # Award loyalty rewards if standard purchase (1 point per ₱30)
    if order.customer_id and order.payment_method != "CREDIT":
        cust = Customer.query.get(order.customer_id)
        cust.accumulated_spend += order.total_amount
        earned_pts = int(order.total_amount // 30)
        if earned_pts > 0:
            cust.points_balance += earned_pts
            ledger = RewardLedger(customer_id=cust.id, points_change=earned_pts, reason=f"Purchase Order #{order.id}")
            db.session.add(ledger)

    db.session.commit()
    flash(f"Order #{order.id} marked Completed & Archived.", "success")
    return redirect(url_for('cashier_terminal'))

# ==================== KITCHEN (KDS) QUEUE ====================

@app.route('/portal/kitchen')
@role_required('ADMIN', 'KITCHEN')
def kitchen_queue():
    active_queue = Order.query.filter(Order.status.in_(['KITCHEN_QUEUE', 'PREPARING'])).order_by(Order.created_at.asc()).all()
    return render_template('kitchen_kds.html', queue=active_queue)

@app.route('/portal/kitchen/update-status/<int:order_id>', methods=['POST'])
@role_required('ADMIN', 'KITCHEN')
def update_kitchen_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status') # PREPARING, READY
    if new_status in ['PREPARING', 'READY']:
        order.status = new_status
        db.session.commit()
    return redirect(url_for('kitchen_queue'))

# ==================== RIDER / DELIVERY PORTAL ====================

@app.route('/portal/rider')
@role_required('ADMIN', 'RIDER')
def rider_portal():
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
    
    # Award loyalty points for completed delivery
    if order.customer_id and order.payment_method != "CREDIT":
        cust = Customer.query.get(order.customer_id)
        earned_pts = int(order.total_amount // 30)
        if earned_pts > 0:
            cust.points_balance += earned_pts
            ledger = RewardLedger(customer_id=cust.id, points_change=earned_pts, reason=f"Delivery Order #{order.id}")
            db.session.add(ledger)
            
    db.session.commit()
    return redirect(url_for('rider_portal'))

# ==================== INVESTOR & ADMIN REPORTING ====================

@app.route('/portal/investor')
@role_required('ADMIN', 'INVESTOR')
def investor_analytics():
    completed_orders = Order.query.filter_by(status="COMPLETED").all()
    total_sales = sum(o.total_amount for o in completed_orders)
    total_orders = len(completed_orders)
    total_ar = sum(c.outstanding_ar for c in Customer.query.all())
    inventory_val = sum(p.stock * p.cost for p in Product.query.all())
    
    return render_template(
        'investor_dashboard.html',
        total_sales=total_sales,
        total_orders=total_orders,
        total_ar=total_ar,
        inventory_val=inventory_val
    )

# ==================== STAFF AUTHENTICATION ====================

@app.route('/staff/login', methods=['GET', 'POST'])
def staff_login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        pin = request.form.get('pin').strip()
        user = Staff.query.filter_by(username=username, active=True).first()
        if user and check_password_hash(user.pin_hash, pin):
            session['staff_user'] = user.username
            session['staff_role'] = user.role
            session.permanent = True
            
            if user.role in ['ADMIN', 'CASHIER']:
                return redirect(url_for('cashier_terminal'))
            elif user.role == 'KITCHEN':
                return redirect(url_for('kitchen_queue'))
            elif user.role == 'RIDER':
                return redirect(url_for('rider_portal'))
            elif user.role == 'INVESTOR':
                return redirect(url_for('investor_analytics'))
        flash("Invalid Staff PIN/Role credentials.", "error")
    return render_template('staff_login.html')

@app.route('/staff/logout')
def staff_logout():
    session.clear()
    return redirect(url_for('staff_login'))

# Database Initializer, Staff Seeder & Auto Menu Loader
with app.app_context():
    # If the schema is outdated, drop and create fresh tables
    try:
        # Check if the existing table has the new schema
        db.session.execute(text("SELECT order_type FROM \"order\" LIMIT 1;"))
    except Exception:
        db.session.rollback()
        # Drop mismatched legacy tables so full POS schema builds cleanly
        db.drop_all()
        db.create_all()
    
    # 1. Site Metrics
    if not SiteMetric.query.first():
        db.session.add(SiteMetric(store_open=True, visitor_count=0))
    
    # 2. Staff Accounts
    default_roles = [
        ('admin', '1234', 'ADMIN'),
        ('cashier1', '1111', 'CASHIER'),
        ('kitchen1', '2222', 'KITCHEN'),
        ('rider1', '3333', 'RIDER'),
        ('investor1', '8888', 'INVESTOR')
    ]
    for user, pin, role in default_roles:
        if not Staff.query.filter_by(username=user).first():
            db.session.add(Staff(username=user, pin_hash=generate_password_hash(pin), role=role))

    # 3. Auto-load 104 Products & Categories
    if not Product.query.first():
        cat_names = [
            "Daily Specials", "Rice Meals", "Ulam", "Street Food", 
            "Coffee-Based", "Drinks", "Shake & Dessert", "Softdrinks", "Printing"
        ]
        for cname in cat_names:
            if not Category.query.filter_by(name=cname).first():
                db.session.add(Category(name=cname))
        db.session.commit()

        menu_data = [
            # Printing
            ("Printing", "Print - Black All Text", 5.0, True, False),
            ("Printing", "Print - Semi Colored", 7.0, True, False),
            ("Printing", "Print - Full Colored", 10.0, True, False),
            ("Printing", "Print - Full Colored HD", 25.0, True, False),

            # Daily Specials
            ("Daily Specials", "Regular Burger", 35.0, True, False),
            ("Daily Specials", "Cheese Burger", 40.0, True, False),
            ("Daily Specials", "Cheesy Fries", 40.0, True, False),
            ("Daily Specials", "Palabok", 50.0, False, False),
            ("Daily Specials", "Pancit Canton", 35.0, True, False),

            # Rice Meals
            ("Rice Meals", "Siomai Rice", 35.0, True, False),
            ("Rice Meals", "Longsilog", 45.0, True, False),
            ("Rice Meals", "Hotsilog", 45.0, True, False),
            ("Rice Meals", "Spamsilog", 45.0, True, False),
            ("Rice Meals", "Tocilog", 45.0, True, False),

            # Street Food
            ("Street Food", "Siomai", 20.0, True, False),
            ("Street Food", "Fishball", 20.0, True, False),
            ("Street Food", "Cheesestick", 20.0, True, False),
            ("Street Food", "Squidball", 20.0, True, False),
            ("Street Food", "Lumpia", 20.0, False, False),
            ("Street Food", "Kikiam", 20.0, True, False),
            ("Street Food", "Tempura", 20.0, True, False),
            ("Street Food", "Fries", 20.0, True, False),

            # Softdrinks
            ("Softdrinks", "Mt. Dew 12oz", 25.0, True, False),
            ("Softdrinks", "Coke Small", 15.0, False, False),
            ("Softdrinks", "Coke 12oz", 25.0, True, False),
            ("Softdrinks", "Coke 1L", 50.0, True, False),
            ("Softdrinks", "Royal Small", 15.0, False, False),
            ("Softdrinks", "Royal 12oz", 25.0, False, False),
            ("Softdrinks", "Sprite Small", 15.0, True, False),
            ("Softdrinks", "Sprite 12oz", 25.0, False, False),

            # Drinks
            ("Drinks", "Lemonade - Blue 12oz", 20.0, False, False),
            ("Drinks", "Lemonade - Blue 16oz", 30.0, False, False),
            ("Drinks", "Lemonade - Blue 1L", 50.0, False, False),
            ("Drinks", "Lemonade - Cucumber 12oz", 20.0, True, False),
            ("Drinks", "Lemonade - Cucumber 16oz", 30.0, True, False),
            ("Drinks", "Lemonade - Cucumber 1L", 50.0, True, False),
            ("Drinks", "Lemonade - Pineapple 12oz", 20.0, True, False),
            ("Drinks", "Lemonade - Pineapple 16oz", 30.0, True, False),
            ("Drinks", "Lemonade - Pineapple 1L", 50.0, True, False),
            ("Drinks", "Fruit Soda - Green Apple 12oz", 40.0, True, False),
            ("Drinks", "Fruit Soda - Green Apple 16oz", 55.0, True, False),
            ("Drinks", "Fruit Soda - Strawberry 12oz", 40.0, True, False),
            ("Drinks", "Fruit Soda - Strawberry 16oz", 55.0, True, False),
            ("Drinks", "Fruit Soda - Blueberry 12oz", 40.0, True, False),
            ("Drinks", "Fruit Soda - Blueberry 16oz", 55.0, True, False),
            ("Drinks", "Fruit Soda - Bubble Gum 12oz", 40.0, True, False),
            ("Drinks", "Fruit Soda - Bubble Gum 16oz", 55.0, True, False),
            ("Drinks", "Fruit Soda - Lychee 12oz", 40.0, True, False),
            ("Drinks", "Fruit Soda - Lychee 16oz", 55.0, True, False),

            # Shake & Dessert
            ("Shake & Dessert", "Ice Scramble - Pink 12oz", 40.0, True, False),
            ("Shake & Dessert", "Ice Scramble - Pink 16oz", 55.0, True, False),
            ("Shake & Dessert", "Ice Scramble - Ube 12oz", 40.0, True, False),
            ("Shake & Dessert", "Ice Scramble - Ube 16oz", 55.0, True, False),
            ("Shake & Dessert", "Float - Coke 12oz", 40.0, True, False),
            ("Shake & Dessert", "Float - Coke 16oz", 55.0, True, False),
            ("Shake & Dessert", "Float - Milo 12oz", 40.0, True, False),
            ("Shake & Dessert", "Float - Milo 16oz", 55.0, True, False),
            ("Shake & Dessert", "Float - Chuckie 12oz", 40.0, True, False),
            ("Shake & Dessert", "Float - Chuckie 16oz", 55.0, True, False),
            ("Shake & Dessert", "Float - Dutchmill 12oz", 40.0, True, False),
            ("Shake & Dessert", "Float - Dutchmill 16oz", 55.0, True, False),
            ("Shake & Dessert", "Shake - Mango 12oz", 40.0, True, False),
            ("Shake & Dessert", "Shake - Mango 16oz", 55.0, True, False),
            ("Shake & Dessert", "Shake - Choco Hot Fudge 12oz", 40.0, False, False),
            ("Shake & Dessert", "Shake - Choco Hot Fudge 16oz", 55.0, False, False),
            ("Shake & Dessert", "Shake - Choco Kisses 12oz", 40.0, False, False),
            ("Shake & Dessert", "Shake - Choco Kisses 16oz", 55.0, False, False),

            # Coffee-Based
            ("Coffee-Based", "Barako Blend Small", 20.0, True, False),
            ("Coffee-Based", "Premium Blend Small", 35.0, True, False),
            ("Coffee-Based", "Macleen's Signature Coffee 12oz", 75.0, False, False),
            ("Coffee-Based", "Hot Latte Small", 50.0, True, False),
            ("Coffee-Based", "Hot Latte 12oz", 85.0, False, False),
            ("Coffee-Based", "Iced Americano 16oz", 55.0, True, False),
            ("Coffee-Based", "Iced Latte 16oz", 70.0, True, False),
            ("Coffee-Based", "Iced Mocha 16oz", 75.0, True, False),
            ("Coffee-Based", "Iced Spanish Latte 16oz", 75.0, True, False),
            ("Coffee-Based", "Iced Premium Latte 16oz", 105.0, True, False),
            ("Coffee-Based", "Macleen's Creamshake Float 16oz", 195.0, True, False),

            # Ulam (Registered for Ulam Voting System)
            ("Ulam", "Laswa", 25.0, False, True),
            ("Ulam", "Utan (Monggo Sayote Manok)", 25.0, False, True),
            ("Ulam", "Paksiw Bangus", 40.0, False, True),
            ("Ulam", "Fried Fish", 30.0, False, True),
            ("Ulam", "Bangus Tinola", 40.0, False, True),
            ("Ulam", "Pork Steak", 50.0, False, True),
            ("Ulam", "Burger Steak", 30.0, False, True),
            ("Ulam", "BIHON", 25.0, False, True),
            ("Ulam", "Pancit", 25.0, False, True),
            ("Ulam", "Bicol Express", 40.0, False, True),
            ("Ulam", "Pinakbet", 25.0, False, True),
            ("Ulam", "Hotdog", 15.0, False, True),
            ("Ulam", "Porkchop", 50.0, False, True),
            ("Ulam", "Pork Adobo", 50.0, False, True),
            ("Ulam", "Tambo", 50.0, False, True),
            ("Ulam", "Torta Talong", 50.0, False, True),
            ("Ulam", "Chicken Menudo", 50.0, False, True),
            ("Ulam", "Tilapia w/ Gata", 45.0, False, True),
            ("Ulam", "Fried Egg - Sunny Side Up", 15.0, False, True),
            ("Ulam", "Fried Egg - Scrambled", 15.0, False, True),
            ("Ulam", "Longganisa", 20.0, False, True),
            ("Ulam", "Utan (Monggo, Kalabasa & Puso w/ Gata)", 25.0, False, True),
            ("Ulam", "Pagi w/ Gata", 35.0, False, True),
            ("Ulam", "Pork Nilaga", 40.0, False, True),
            ("Ulam", "Spam", 20.0, False, True),
            ("Ulam", "Tocino", 20.0, False, True)
        ]

        for cat_name, p_name, price, active, is_ulam in menu_data:
            db.session.add(Product(
                name=p_name,
                category_name=cat_name,
                price=price,
                stock=100,
                is_active=active,
                is_ulam=is_ulam,
                image_url="https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=500"
            ))

    db.session.commit()