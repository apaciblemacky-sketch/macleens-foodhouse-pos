import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'macleens-crafts-secure-key-2026')

database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///crafts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db = SQLAlchemy(app)

# Database Models
class AdminConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    password_hash = db.Column(db.String(255), nullable=False)

class SiteVisitor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    total_visits = db.Column(db.Integer, default=0)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    image_url = db.Column(db.String(255), default="https://images.unsplash.com/photo-1513519245088-0e12902e5a38?w=500&auto=format&fit=crop")
    items = db.relationship('CraftItem', backref='category_rel', lazy=True)

class CraftItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(255), default="https://images.unsplash.com/photo-1513519245088-0e12902e5a38?w=500&auto=format&fit=crop")
    category_name = db.Column(db.String(80), db.ForeignKey('category.name'), nullable=True, default="General")
    
    # Inventory & Featured Settings
    availability_type = db.Column(db.String(20), default="In Stock")
    stock_quantity = db.Column(db.Integer, default=10)
    is_top_seller = db.Column(db.Boolean, default=False)
    is_featured = db.Column(db.Boolean, default=False)
    
    likes = db.Column(db.Integer, default=0)
    views = db.Column(db.Integer, default=0)
    orders_count = db.Column(db.Integer, default=0)
    comments = db.relationship('Comment', backref='craft_item', cascade="all, delete-orphan", lazy=True)
    orders = db.relationship('Order', backref='craft_item', cascade="all, delete-orphan", lazy=True)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(80), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    item_id = db.Column(db.Integer, db.ForeignKey('craft_item.id'), nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    contact_number = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    fb_account = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    pickup_location = db.Column(db.String(150), default="Macleen's Food House")
    status = db.Column(db.String(50), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    item_id = db.Column(db.Integer, db.ForeignKey('craft_item.id'), nullable=False)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== PUBLIC STORE ====================

@app.route('/')
def index():
    # Track Site Visitors
    visitor_record = SiteVisitor.query.first()
    if not visitor_record:
        visitor_record = SiteVisitor(total_visits=1)
        db.session.add(visitor_record)
    else:
        visitor_record.total_visits += 1
    db.session.commit()

    selected_category = request.args.get('category')
    categories = Category.query.all()
    
    top_sellers = CraftItem.query.filter_by(is_top_seller=True).all()
    featured_items = CraftItem.query.filter_by(is_featured=True).all()

    if selected_category:
        items = CraftItem.query.filter_by(category_name=selected_category).all()
    else:
        items = CraftItem.query.all()

    return render_template(
        'index.html',
        items=items,
        categories=categories,
        selected_category=selected_category,
        top_sellers=top_sellers,
        featured_items=featured_items,
        site_visits=visitor_record.total_visits
    )

@app.route('/item/<int:item_id>')
def item_detail(item_id):
    item = CraftItem.query.get_or_404(item_id)
    item.views += 1
    db.session.commit()
    return render_template('item_detail.html', item=item)

@app.route('/like/<int:item_id>', methods=['POST'])
def like_item(item_id):
    item = CraftItem.query.get_or_404(item_id)
    item.likes += 1
    db.session.commit()
    return redirect(url_for('item_detail', item_id=item_id))

@app.route('/comment/<int:item_id>', methods=['POST'])
def add_comment(item_id):
    author = request.form.get('author', '').strip() or 'Anonymous Customer'
    content = request.form.get('content', '').strip()
    if content:
        new_comment = Comment(author=author, content=content, item_id=item_id)
        db.session.add(new_comment)
        db.session.commit()
    return redirect(url_for('item_detail', item_id=item_id))

@app.route('/order/<int:item_id>', methods=['GET', 'POST'])
def order_item(item_id):
    item = CraftItem.query.get_or_404(item_id)
    error = None
    if request.method == 'POST':
        name = request.form.get('customer_name', '').strip()
        contact = request.form.get('contact_number', '').strip()
        email = request.form.get('email', '').strip()
        fb = request.form.get('fb_account', '').strip()
        quantity = int(request.form.get('quantity', 1))

        if item.availability_type == "In Stock" and quantity > item.stock_quantity:
            error = f"Sorry, only {item.stock_quantity} item(s) currently available in stock."
        elif name and contact and email and fb and quantity > 0:
            total = item.price * quantity
            if item.availability_type == "In Stock":
                item.stock_quantity -= quantity

            new_order = Order(
                customer_name=name,
                contact_number=contact,
                email=email,
                fb_account=fb,
                quantity=quantity,
                total_price=total,
                item_id=item.id
            )
            item.orders_count += quantity
            db.session.add(new_order)
            db.session.commit()
            return render_template('order_success.html', order=new_order, item=item)

    return render_template('order_form.html', item=item, error=error)

# ==================== ADMIN ROUTES ====================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        entered_password = request.form.get('password', '')
        config = AdminConfig.query.first()
        if config and check_password_hash(config.password_hash, entered_password):
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        error = "Incorrect password. Please try again."
    return render_template('admin_login.html', error=error)

@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('index'))

@app.route('/admin/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    message = None
    error = None
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        config = AdminConfig.query.first()
        if not check_password_hash(config.password_hash, current_password):
            error = "Current password is incorrect."
        elif len(new_password) < 4:
            error = "New password must be at least 4 characters long."
        elif new_password != confirm_password:
            error = "New passwords do not match."
        else:
            config.password_hash = generate_password_hash(new_password)
            db.session.commit()
            message = "Password updated successfully!"

    return render_template('change_password.html', message=message, error=error)

@app.route('/admin')
@login_required
def admin_dashboard():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    items = CraftItem.query.all()
    categories = Category.query.all()
    visitor_record = SiteVisitor.query.first()

    total_views = sum(i.views for i in items)
    total_likes = sum(i.likes for i in items)
    total_orders = len(orders)
    total_revenue = sum(o.total_price for o in orders)
    completed_orders = sum(1 for o in orders if o.status == "Completed")
    
    low_stock_items = [i for i in items if i.availability_type == "In Stock" and i.stock_quantity <= 3]
    out_of_stock_items = [i for i in items if i.availability_type == "In Stock" and i.stock_quantity == 0]

    metrics = {
        "site_visits": visitor_record.total_visits if visitor_record else 0,
        "total_views": total_views,
        "total_likes": total_likes,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "completed_orders": completed_orders,
        "low_stock_count": len(low_stock_items),
        "out_of_stock_count": len(out_of_stock_items)
    }
    return render_template('admin.html', items=items, orders=orders, categories=categories, metrics=metrics)

@app.route('/admin/toggle-featured/<int:item_id>', methods=['POST'])
@login_required
def toggle_featured(item_id):
    item = CraftItem.query.get_or_404(item_id)
    item.is_featured = not item.is_featured
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/toggle-top-seller/<int:item_id>', methods=['POST'])
@login_required
def toggle_top_seller(item_id):
    item = CraftItem.query.get_or_404(item_id)
    item.is_top_seller = not item.is_top_seller
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add-item', methods=['GET', 'POST'])
@login_required
def add_item():
    categories = Category.query.all()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = float(request.form.get('price', 0.0))
        category_name = request.form.get('category_name', 'General')
        availability_type = request.form.get('availability_type', 'In Stock')
        stock_quantity = int(request.form.get('stock_quantity', 0)) if availability_type == 'In Stock' else 0
        is_top_seller = True if request.form.get('is_top_seller') else False
        is_featured = True if request.form.get('is_featured') else False
        
        image_url = "https://images.unsplash.com/photo-1513519245088-0e12902e5a38?w=500&auto=format&fit=crop"
        file = request.files.get('image')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            image_url = f"/static/uploads/{filename}"

        new_item = CraftItem(
            name=name, 
            description=description, 
            price=price, 
            category_name=category_name, 
            availability_type=availability_type,
            stock_quantity=stock_quantity,
            is_top_seller=is_top_seller,
            is_featured=is_featured,
            image_url=image_url
        )
        db.session.add(new_item)
        db.session.commit()
        return redirect(url_for('admin_dashboard'))

    return render_template('add_item.html', categories=categories)

@app.route('/admin/edit-item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    item = CraftItem.query.get_or_404(item_id)
    categories = Category.query.all()
    if request.method == 'POST':
        item.name = request.form.get('name', item.name).strip()
        item.description = request.form.get('description', item.description).strip()
        item.price = float(request.form.get('price', item.price))
        item.category_name = request.form.get('category_name', item.category_name)
        item.availability_type = request.form.get('availability_type', 'In Stock')
        item.stock_quantity = int(request.form.get('stock_quantity', 0)) if item.availability_type == 'In Stock' else 0
        item.is_top_seller = True if request.form.get('is_top_seller') else False
        item.is_featured = True if request.form.get('is_featured') else False

        file = request.files.get('image')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            item.image_url = f"/static/uploads/{filename}"

        db.session.commit()
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_item.html', item=item, categories=categories)

@app.route('/admin/duplicate-item/<int:item_id>', methods=['POST'])
@login_required
def duplicate_item(item_id):
    original = CraftItem.query.get_or_404(item_id)
    duplicated = CraftItem(
        name=f"{original.name} (Copy)",
        description=original.description,
        price=original.price,
        image_url=original.image_url,
        category_name=original.category_name,
        availability_type=original.availability_type,
        stock_quantity=original.stock_quantity,
        is_top_seller=original.is_top_seller,
        is_featured=original.is_featured
    )
    db.session.add(duplicated)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete-item/<int:item_id>', methods=['POST'])
@login_required
def delete_item(item_id):
    item = CraftItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add-category', methods=['POST'])
@login_required
def add_category():
    cat_name = request.form.get('cat_name', '').strip()
    image_url = "https://images.unsplash.com/photo-1513519245088-0e12902e5a38?w=500&auto=format&fit=crop"

    file = request.files.get('cat_image')
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        image_url = f"/static/uploads/{filename}"

    if cat_name and not Category.query.filter_by(name=cat_name).first():
        new_cat = Category(name=cat_name, image_url=image_url)
        db.session.add(new_cat)
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete-category/<int:cat_id>', methods=['POST'])
@login_required
def delete_category(cat_id):
    category = Category.query.get_or_404(cat_id)
    items_in_category = CraftItem.query.filter_by(category_name=category.name).all()
    for item in items_in_category:
        item.category_name = "General"
    db.session.delete(category)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/order-status/<int:order_id>', methods=['POST'])
@login_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    if new_status in ['Pending', 'Ready for Pickup', 'Completed']:
        order.status = new_status
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

# App Startup Initialization & Auto-Migration
with app.app_context():
    db.create_all()

    # Automatically add new columns if they do not exist
    with db.engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE craft_item ADD COLUMN IF NOT EXISTS availability_type VARCHAR(20) DEFAULT 'In Stock';"))
            conn.execute(text("ALTER TABLE craft_item ADD COLUMN IF NOT EXISTS stock_quantity INTEGER DEFAULT 10;"))
            conn.execute(text("ALTER TABLE craft_item ADD COLUMN IF NOT EXISTS is_top_seller BOOLEAN DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE craft_item ADD COLUMN IF NOT EXISTS is_featured BOOLEAN DEFAULT FALSE;"))
            conn.commit()
        except Exception as e:
            print("Migration Note:", e)

    if not AdminConfig.query.first():
        default_admin = AdminConfig(password_hash=generate_password_hash("hederaadmin"))
        db.session.add(default_admin)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)