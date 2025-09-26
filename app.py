from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import unittest # Import unittest for the test case
from flask_testing import TestCase # Import TestCase for Flask testing

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_secret_key_here')

# Database URI: Use DATABASE_URL if available (e.g., PostgreSQL on Railway), else fallback to SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.join(os.getcwd(), "instance", "database.db")}')
 
# Ensure upload folder exists
upload_folder = os.path.join(app.root_path, 'static', 'uploads')
if not os.path.exists(upload_folder):
    os.makedirs(upload_folder)
app.config['UPLOAD_FOLDER'] = upload_folder

# Initialize db
db = SQLAlchemy()

# Initialize the database with the app
db.init_app(app)

# Ensure instance folder exists for SQLite
if not os.path.exists('instance'):
    os.makedirs('instance')

# Create tables if they don't exist
with app.app_context():
    db.create_all()



# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'admin', 'orders', 'production', 'inventory'

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    details = db.Column(db.Text, nullable=False)
    order_type = db.Column(db.String(10), nullable=False, default='in')  # 'in' or 'out'
    date = db.Column(db.DateTime, nullable=False, default=db.func.now())
    product_name = db.Column(db.String(150), nullable=False)
    size = db.Column(db.String(50), nullable=True)
    product_photo = db.Column(db.String(150), nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    available_balance = db.Column(db.Integer, nullable=False, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Production(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    details = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=db.func.now())
    product_name = db.Column(db.String(150), nullable=False)
    size = db.Column(db.String(50), nullable=False)
    packing = db.Column(db.String(50), nullable=True)
    product_photo = db.Column(db.String(150), nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    broken_quantity = db.Column(db.Integer, nullable=False, default=0)
    available_balance = db.Column(db.Integer, nullable=False, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_type = db.Column(db.String(50), nullable=False)  # 'box', 'carton', 'glass'
    quantity = db.Column(db.Integer, nullable=False)
    packing = db.Column(db.String(50), nullable=True)
    action = db.Column(db.String(10), nullable=False)  # 'in', 'out'
    image_filename = db.Column(db.String(150), nullable=True)
    date = db.Column(db.DateTime, nullable=False, default=db.func.now())
    product_name = db.Column(db.String(150), nullable=False)
    size = db.Column(db.String(50), nullable=False)
    # Removed product_photo field as per request
    broken_quantity = db.Column(db.Integer, nullable=False, default=0)
    available_balance = db.Column(db.Integer, nullable=False, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Helper function to get current user or redirect
def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return User.query.get(user_id)

# Routes
@app.route('/')
def index():
    user = get_current_user()
    if user:
        return render_template('dashboard.html', user=user)
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials')
    else:
        # Consume flashed messages on GET to clear old messages
        from flask import get_flashed_messages
        get_flashed_messages()
    return render_template('login.html', user=None)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))



@app.route('/orders')
def orders():
    user = get_current_user()
    if not user or user.role not in ['admin', 'orders']:
        return redirect(url_for('index'))
    if user.role in ['admin', 'orders']:
        orders = Order.query.all()
    else:
        orders = Order.query.filter_by(user_id=user.id).all()
    # Fetch production available balance per product
    production_balances = {}
    productions = Production.query.all()
    for prod in productions:
        production_balances[prod.product_name] = prod.available_balance
    return render_template('orders.html', orders=orders, user=user, production_balances=production_balances)

@app.route('/add_order', methods=['GET', 'POST'])
def add_order():
    user = get_current_user()
    if not user or user.role not in ['admin', 'orders']:
        return redirect(url_for('index'))
    if request.method == 'POST':
        details = request.form['details']
        receive_date_str = request.form.get('receive_date', '').strip()
        deliver_date_str = request.form.get('deliver_date', '').strip()

        # Determine order_type and date based on provided date
        if receive_date_str and not deliver_date_str:
            order_type = 'in'
            try:
                date = datetime.strptime(receive_date_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid receive date format. Use YYYY-MM-DD.')
                return redirect(url_for('add_order'))
        elif deliver_date_str and not receive_date_str:
            order_type = 'out'
            try:
                date = datetime.strptime(deliver_date_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid deliver date format. Use YYYY-MM-DD.')
                return redirect(url_for('add_order'))
        else:
            # Default to 'in' with current date if no date or both provided
            order_type = 'in'
            date = datetime.now()

        product_name = request.form['product_name']
        # Convert size from "length - width - height" in cm to a standardized format
        size_input = request.form.get('size', '').strip()
        if size_input:
            size_parts = [part.strip() for part in size_input.split('-')]
            if len(size_parts) == 3 and all(part.replace('.', '', 1).isdigit() for part in size_parts):
                size = f"{size_parts[0]}cm x {size_parts[1]}cm x {size_parts[2]}cm"
            else:
                size = size_input  # Keep original if format is unexpected
        else:
            size = None
        quantity = int(request.form['quantity'])
        product_photo = None
        if 'product_photo' in request.files:
            file = request.files['product_photo']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                product_photo = filename
        # Calculate available_balance
        all_orders = Order.query.filter_by(product_name=product_name).all()
        current_total = sum(o.quantity if o.order_type == 'in' else -o.quantity for o in all_orders)
        if order_type == 'in':
            available_balance = current_total + quantity
        else:
            available_balance = current_total - quantity
        new_order = Order(details=details, order_type=order_type, date=date, product_name=product_name, size=size, product_photo=product_photo, quantity=quantity, available_balance=available_balance, user_id=user.id)
        db.session.add(new_order)
        db.session.commit()
        return redirect(url_for('orders'))
    return render_template('add_order.html', user=user)

@app.route('/edit_order/<int:order_id>', methods=['GET', 'POST'])
def edit_order(order_id):
    user = get_current_user()
    if not user or user.role not in ['admin', 'orders']:
        return redirect(url_for('index'))
    order = Order.query.get_or_404(order_id)
    if user.role != 'admin' and order.user_id != user.id:
        return redirect(url_for('orders'))
    if request.method == 'POST':
        order.details = request.form['details']
        receive_date_str = request.form.get('receive_date', '').strip()
        deliver_date_str = request.form.get('deliver_date', '').strip()

        # Determine order_type and date based on provided date
        if receive_date_str and not deliver_date_str:
            order_type = 'in'
            try:
                date = datetime.strptime(receive_date_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid receive date format. Use YYYY-MM-DD.')
                return redirect(url_for('edit_order', order_id=order_id))
        elif deliver_date_str and not receive_date_str:
            order_type = 'out'
            try:
                date = datetime.strptime(deliver_date_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid deliver date format. Use YYYY-MM-DD.')
                return redirect(url_for('edit_order', order_id=order_id))
        else:
            flash('Please provide either receive date or deliver date, but not both.')
            return redirect(url_for('edit_order', order_id=order_id))

        order.order_type = order_type
        old_product_name = order.product_name
        order.product_name = request.form['product_name']
        # Convert size from "length - width - height" in cm to a standardized format
        size_input = request.form['size']
        size_parts = [part.strip() for part in size_input.split('-')]
        if len(size_parts) == 3 and all(part.replace('.', '', 1).isdigit() for part in size_parts):
            order.size = f"{size_parts[0]}cm x {size_parts[1]}cm x {size_parts[2]}cm"
        else:
            order.size = size_input  # Keep original if format is unexpected
        order.quantity = int(request.form['quantity'])
        if 'product_photo' in request.files:
            file = request.files['product_photo']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                order.product_photo = filename
        # Recalculate available_balance for all orders of the old and new product
        for product in [old_product_name, order.product_name]:
            if product:
                all_orders = Order.query.filter_by(product_name=product).order_by(Order.id).all()
                current_total = 0
                for o in all_orders:
                    if o.order_type == 'in':
                        current_total += o.quantity
                    else:
                        current_total -= o.quantity
                    o.available_balance = current_total
        db.session.commit()
        return redirect(url_for('orders'))
    return render_template('edit_order.html', order=order, user=user)

@app.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    user = get_current_user()
    if not user or user.role not in ['admin', 'orders']:
        return redirect(url_for('index'))
    order = Order.query.get_or_404(order_id)
    if user.role != 'admin' and order.user_id != user.id:
        return redirect(url_for('orders'))
    db.session.delete(order)
    db.session.commit()
    return redirect(url_for('orders'))

# Temporary route to delete order by details for immediate deletion
@app.route('/delete_order_by_details', methods=['POST'])
def delete_order_by_details():
    user = get_current_user()
    if not user or user.role not in ['admin', 'orders']:
        return redirect(url_for('index'))
    details = request.form.get('details')
    if not details:
        return "No details provided", 400
    order = Order.query.filter_by(details=details).first()
    if not order:
        return "Order not found", 404
    if user.role != 'admin' and order.user_id != user.id:
        return redirect(url_for('orders'))
    db.session.delete(order)
    db.session.commit()
    return "Order deleted", 200

@app.route('/production')
def production():
    user = get_current_user()
    if not user or user.role not in ['admin', 'production']:
        return redirect(url_for('index'))
    if user.role == 'admin':
        productions = Production.query.all()
    else:
        productions = Production.query.filter_by(user_id=user.id).all()
    return render_template('production.html', productions=productions, user=user)

@app.route('/add_production', methods=['GET', 'POST'])
def add_production():
    user = get_current_user()
    if not user or user.role not in ['admin', 'production']:
        return redirect(url_for('index'))
    if request.method == 'POST':
        details = request.form['details']
        date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        product_name = request.form['product_name']
        # Convert size from "length - width - height" in cm to a standardized format
        size_input = request.form['size']
        size_parts = [part.strip() for part in size_input.split('-')]
        if len(size_parts) == 3 and all(part.replace('.', '', 1).isdigit() for part in size_parts):
            size = f"{size_parts[0]}cm x {size_parts[1]}cm x {size_parts[2]}cm"
        else:
            size = size_input  # Keep original if format is unexpected
        quantity = int(request.form['quantity'])
        broken_quantity = int(request.form.get('broken_quantity', 0))
        packing = request.form.get('packing', '')
        product_photo = None
        if 'product_photo' in request.files:
            file = request.files['product_photo']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                product_photo = filename
        # Calculate available_balance
        all_productions = Production.query.filter_by(product_name=product_name).all()
        current_total = sum(p.quantity for p in all_productions)
        available_balance = current_total + quantity - broken_quantity
        new_production = Production(details=details, date=date, product_name=product_name, size=size, packing=packing, product_photo=product_photo, quantity=quantity, broken_quantity=broken_quantity, available_balance=available_balance, user_id=user.id)
        db.session.add(new_production)
        db.session.commit()
        return redirect(url_for('production'))
    return render_template('add_production.html', user=user)

@app.route('/edit_production/<int:production_id>', methods=['GET', 'POST'])
def edit_production(production_id):
    user = get_current_user()
    if not user or user.role not in ['admin', 'production']:
        return redirect(url_for('index'))
    production = Production.query.get_or_404(production_id)
    if user.role != 'admin' and production.user_id != user.id:
        return redirect(url_for('production'))
    if request.method == 'POST':
        production.details = request.form['details']
        production.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        old_product_name = production.product_name
        production.product_name = request.form['product_name']
        # Convert size from "length - width - height" in cm to a standardized format
        size_input = request.form['size']
        size_parts = [part.strip() for part in size_input.split('-')]
        if len(size_parts) == 3 and all(part.replace('.', '', 1).isdigit() for part in size_parts):
            production.size = f"{size_parts[0]}cm x {size_parts[1]}cm x {size_parts[2]}cm"
        else:
            production.size = size_input  # Keep original if format is unexpected
        production.quantity = int(request.form['quantity'])
        production.broken_quantity = int(request.form.get('broken_quantity', 0))
        production.packing = request.form.get('packing', '')
        if 'product_photo' in request.files:
            file = request.files['product_photo']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                production.product_photo = filename
        # Recalculate available_balance for all productions of the old and new product
        for product in [old_product_name, production.product_name]:
            if product:
                all_productions = Production.query.filter_by(product_name=product).order_by(Production.id).all()
                current_total = 0
                for p in all_productions:
                    current_total += p.quantity
                    p.available_balance = current_total - p.broken_quantity
        db.session.commit()
        return redirect(url_for('production'))
    return render_template('edit_production.html', production=production, user=user)

@app.route('/delete_production/<int:production_id>', methods=['POST'])
def delete_production(production_id):
    user = get_current_user()
    if not user or user.role not in ['admin', 'production']:
        return redirect(url_for('index'))
    production = Production.query.get_or_404(production_id)
    if user.role != 'admin' and production.user_id != user.id:
        return redirect(url_for('production'))
    db.session.delete(production)
    db.session.commit()
    return redirect(url_for('production'))

@app.route('/inventory')
def inventory():
    user = get_current_user()
    if not user or user.role not in ['admin', 'inventory']:
        return redirect(url_for('index'))
    if user.role == 'admin':
        inventories = Inventory.query.all()
    else:
        inventories = Inventory.query.filter_by(user_id=user.id).all()
    return render_template('inventory.html', inventories=inventories, user=user)

@app.route('/add_inventory', methods=['GET', 'POST'])
def add_inventory():
    user = get_current_user()
    if not user or user.role not in ['admin', 'inventory']:
        return redirect(url_for('index'))
    if request.method == 'POST':
        item_type = request.form['item_type']
        quantity = int(request.form['quantity'])
        broken_quantity = int(request.form.get('broken_quantity', 0))
        action = request.form['action']
        date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        product_name = request.form['product_name']
        # Convert size from "length - width - height" in cm to a standardized format
        size_input = request.form['size']
        size_parts = [part.strip() for part in size_input.split('-')]
        if len(size_parts) == 3 and all(part.replace('.', '', 1).isdigit() for part in size_parts):
            size = f"{size_parts[0]}cm x {size_parts[1]}cm x {size_parts[2]}cm"
        else:
            size = size_input  # Keep original if format is unexpected
        image_filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_filename = filename
        # Calculate available_balance
        all_inventories = Inventory.query.filter_by(product_name=product_name, size=size, item_type=item_type).all()
        current_total = sum(inv.quantity if inv.action == 'in' else -inv.quantity for inv in all_inventories)
        if action == 'out' and quantity > current_total:
            flash(f'Insufficient balance. Available: {current_total}')
            return redirect(url_for('add_inventory'))
        if action == 'in':
            available_balance = current_total + quantity
        else:
            available_balance = current_total - quantity
        packing = request.form.get('packing', '')
        available_balance -= broken_quantity
        new_inventory = Inventory(item_type=item_type, quantity=quantity, packing=packing, action=action, date=date, product_name=product_name, size=size, broken_quantity=broken_quantity, available_balance=available_balance, image_filename=image_filename, user_id=user.id)
        db.session.add(new_inventory)
        db.session.commit()
        return redirect(url_for('inventory'))
    return render_template('add_inventory.html', user=user)

@app.route('/edit_inventory/<int:inventory_id>', methods=['GET', 'POST'])
def edit_inventory(inventory_id):
    user = get_current_user()
    if not user or user.role not in ['admin', 'inventory']:
        return redirect(url_for('index'))
    inventory = Inventory.query.get_or_404(inventory_id)
    if user.role != 'admin' and inventory.user_id != user.id:
        return redirect(url_for('inventory'))
    if request.method == 'POST':
        old_product_name = inventory.product_name
        old_size = inventory.size
        old_item_type = inventory.item_type
        old_quantity = inventory.quantity
        old_action = inventory.action
        inventory.item_type = request.form['item_type']
        inventory.quantity = int(request.form['quantity'])
        inventory.broken_quantity = int(request.form.get('broken_quantity', 0))
        inventory.action = request.form['action']
        inventory.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        inventory.product_name = request.form['product_name']
        # Convert size from "length - width - height" in cm to a standardized format
        size_input = request.form['size']
        size_parts = [part.strip() for part in size_input.split('-')]
        if len(size_parts) == 3 and all(part.replace('.', '', 1).isdigit() for part in size_parts):
            inventory.size = f"{size_parts[0]}cm x {size_parts[1]}cm x {size_parts[2]}cm"
        else:
            inventory.size = size_input  # Keep original if format is unexpected
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                inventory.image_filename = filename
        # Check for sufficient balance if action is 'out'
        all_inventories = Inventory.query.filter(Inventory.product_name == inventory.product_name, Inventory.size == inventory.size, Inventory.item_type == inventory.item_type, Inventory.id != inventory.id).all()
        current_total = sum(inv.quantity if inv.action == 'in' else -inv.quantity for inv in all_inventories)
        if inventory.action == 'out' and inventory.quantity > current_total:
            flash(f'Insufficient balance. Available: {current_total}')
            return redirect(url_for('edit_inventory', inventory_id=inventory_id))
        # Recalculate available_balance for all inventories of the old and new combination
        combinations = [
            (old_product_name, old_size, old_item_type),
            (inventory.product_name, inventory.size, inventory.item_type)
        ]
        for product, size, item_type in combinations:
            if product and size and item_type:
                all_inventories = Inventory.query.filter_by(product_name=product, size=size, item_type=item_type).order_by(Inventory.id).all()
                current_total = 0
                for inv in all_inventories:
                    if inv.action == 'in':
                        current_total += inv.quantity
                    else:
                        current_total -= inv.quantity
                    inv.available_balance = current_total - inv.broken_quantity
        db.session.commit()
        return redirect(url_for('inventory'))
    return render_template('edit_inventory.html', inventory=inventory, user=user)

@app.route('/delete_inventory/<int:inventory_id>', methods=['POST'])
def delete_inventory(inventory_id):
    user = get_current_user()
    if not user or user.role not in ['admin', 'inventory']:
        return redirect(url_for('index'))
    inventory = Inventory.query.get_or_404(inventory_id)
    if user.role != 'admin' and inventory.user_id != user.id:
        return redirect(url_for('inventory'))
    db.session.delete(inventory)
    db.session.commit()
    return redirect(url_for('inventory'))

@app.route('/admin')
def admin():
    user = get_current_user()
    if not user or user.role != 'admin':
        return redirect(url_for('index'))
    users = User.query.all()
    return render_template('admin.html', users=users, user=user)

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    user = get_current_user()
    if not user or user.role != 'admin':
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('add_user'))
        new_user = User(username=username, password=generate_password_hash(password), role=role)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('admin'))
    return render_template('add_user.html', user=user)

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    user = get_current_user()
    if not user or user.role != 'admin':
        return redirect(url_for('index'))
    edit_user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        edit_user.username = request.form['username']
        password = request.form['password']
        if password:
            edit_user.password = generate_password_hash(password)
        edit_user.role = request.form['role']
        db.session.commit()
        return redirect(url_for('admin'))
    return render_template('edit_user.html', edit_user=edit_user, user=user)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    user = get_current_user()
    if not user or user.role != 'admin':
        return redirect(url_for('index'))
    del_user = User.query.get_or_404(user_id)
    db.session.delete(del_user)
    db.session.commit()
    return redirect(url_for('admin'))

from sqlalchemy import func
from sqlalchemy.sql.expression import case

@app.route('/api/check_inventory_balance')
def check_inventory_balance():
    product_name = request.args.get('product_name', '').strip()
    size = request.args.get('size', '').strip()
    item_type = request.args.get('item_type', '').strip()
    inventory_id = request.args.get('inventory_id', '').strip()
    if not product_name or not size or not item_type:
        return jsonify({'available_balance': 0})
    query = Inventory.query.filter_by(product_name=product_name, size=size, item_type=item_type)
    if inventory_id:
        query = query.filter(Inventory.id != int(inventory_id))
    all_inventories = query.all()
    current_total = sum(inv.quantity if inv.action == 'in' else -inv.quantity for inv in all_inventories)
    available_balance = current_total - sum(inv.broken_quantity for inv in all_inventories)
    return jsonify({'available_balance': available_balance})

@app.route('/search')
def search():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    query = request.args.get('q', '').strip()
    orders = []
    productions = []
    inventories = []
    if query:
        # Aggregate available balance by product_name for orders
        orders = db.session.query(
            Order.product_name,
            func.max(Order.available_balance).label('available_balance')
        ).filter(
            (Order.product_name.ilike(f'%{query}%')) | (Order.details.ilike(f'%{query}%'))
        ).group_by(Order.product_name).all()

        # Aggregate available balance by product_name for productions
        productions = db.session.query(
            Production.product_name,
            func.max(Production.available_balance).label('available_balance')
        ).filter(
            (Production.product_name.ilike(f'%{query}%')) | (Production.details.ilike(f'%{query}%'))
        ).group_by(Production.product_name).all()

        # Aggregate net available balance by product_name for inventories considering 'in' and 'out' actions
        inventories = db.session.query(
            Inventory.product_name,
            (func.sum(
                case(
                    (Inventory.action == 'in', Inventory.quantity),
                    (Inventory.action == 'out', -Inventory.quantity),
                    else_=0
                )
            ) - func.sum(Inventory.broken_quantity)).label('available_balance')
        ).filter(
            Inventory.product_name.ilike(f'%{query}%')
        ).group_by(Inventory.product_name).all()

    return render_template('search_results.html', user=user, query=query, orders=orders, productions=productions, inventories=inventories)

# Test Case (assuming this was in a separate test_app.py file)
class ElMasaTestCase(TestCase):

    def create_app(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:' # Use in-memory SQLite for tests
        app.config['SECRET_KEY'] = 'test_secret_key' # Set a secret key for testing
        return app

    def setUp(self):
        with app.app_context():
            db.engine.dispose()
            db.drop_all()
            db.create_all()
        # Create sample users for tests only if they don't exist
        with app.app_context():
            if not User.query.filter_by(username='admin').first():
                admin = User(username='admin', password=generate_password_hash('admin123'), role='admin')
                db.session.add(admin)
            if not User.query.filter_by(username='Ahmed').first():
                orders_user = User(username='Ahmed', password=generate_password_hash('ahmed123'), role='orders')
                db.session.add(orders_user)
            if not User.query.filter_by(username='Ashraf').first():
                production_user = User(username='Ashraf', password=generate_password_hash('ashraf123'), role='production')
                db.session.add(production_user)
            if not User.query.filter_by(username='Mohammed').first():
                inventory_user = User(username='Mohammed', password=generate_password_hash('mohammed123'), role='inventory')
                db.session.add(inventory_user)
            db.session.commit()

    def tearDown(self):
        with app.app_context():
            db.session.rollback()
            db.drop_all()
            db.engine.dispose()
        db.session.remove()

    def test_crud_order(self):
        # Example test for order creation (you would expand this)
        with self.client:
            # Log in as admin to create an order
            self.client.post('/login', data=dict(username='admin', password='admin123'), follow_redirects=True)

            # Add an order
            response = self.client.post('/add_order', data={
                'details': 'Test Order Details',
                'receive_date': '2023-01-01',
                'product_name': 'Test Product',
                'size': 'Large',
                'quantity': 10
            }, follow_redirects=True)
            self.assertIn(b'Test Order Details', response.data)

            # Verify the order was added
            order = Order.query.filter_by(product_name='Test Product').first()
            self.assertIsNotNone(order)
            self.assertEqual(order.details, 'Test Order Details')

            # Edit the order
            response = self.client.post(f'/edit_order/{order.id}', data={
                'details': 'Updated Order Details',
                'deliver_date': '2023-01-02',
                'product_name': 'Updated Product',
                'size': 'Small',
                'quantity': 5
            }, follow_redirects=True)
            self.assertIn(b'Updated Order Details', response.data)

            # Verify the order was updated
            updated_order = Order.query.get(order.id)
            self.assertEqual(updated_order.details, 'Updated Order Details')
            self.assertEqual(updated_order.order_type, 'out')

            # Delete the order
            response = self.client.post(f'/delete_order/{order.id}', follow_redirects=True)
            self.assertNotIn(b'Updated Order Details', response.data) # Assuming orders page no longer shows it

            # Verify the order was deleted
            deleted_order = Order.query.get(order.id)
            self.assertIsNone(deleted_order)

    def test_crud_production(self):
        with self.client:
            # Log in as production user
            self.client.post('/login', data=dict(username='Ashraf', password='ashraf123'), follow_redirects=True)

            # Add production
            response = self.client.post('/add_production', data={
                'details': 'Test Production Details',
                'date': '2023-01-01',
                'product_name': 'Test Product',
                'size': '10cm x 20cm x 30cm',
                'quantity': 10,
                'broken_quantity': 1
            }, follow_redirects=True)
            self.assertIn(b'Test Production Details', response.data)

            # Verify production was added
            production = Production.query.filter_by(product_name='Test Product').first()
            self.assertIsNotNone(production)
            self.assertEqual(production.details, 'Test Production Details')
            self.assertEqual(production.available_balance, 9)  # 10 - 1

            # Edit production
            response = self.client.post(f'/edit_production/{production.id}', data={
                'details': 'Updated Production Details',
                'date': '2023-01-02',
                'product_name': 'Updated Product',
                'size': '15cm x 25cm x 35cm',
                'quantity': 15,
                'broken_quantity': 2
            }, follow_redirects=True)
            self.assertIn(b'Updated Production Details', response.data)

            # Verify production was updated
            updated_production = Production.query.get(production.id)
            self.assertEqual(updated_production.details, 'Updated Production Details')
            self.assertEqual(updated_production.available_balance, 13)  # 15 - 2

            # Delete production
            response = self.client.post(f'/delete_production/{production.id}', follow_redirects=True)
            self.assertNotIn(b'Updated Production Details', response.data)

            # Verify production was deleted
            deleted_production = Production.query.get(production.id)
            self.assertIsNone(deleted_production)

    def test_crud_inventory(self):
        with self.client:
            # Log in as inventory user
            self.client.post('/login', data=dict(username='Mohammed', password='mohammed123'), follow_redirects=True)

            # Add inventory
            response = self.client.post('/add_inventory', data={
                'item_type': 'box',
                'quantity': 10,
                'broken_quantity': 1,
                'action': 'in',
                'date': '2023-01-01',
                'product_name': 'Test Product',
                'size': '10cm x 20cm x 30cm'
            }, follow_redirects=True)
            self.assertIn(b'Test Product', response.data)

            # Verify inventory was added
            inventory = Inventory.query.filter_by(product_name='Test Product').first()
            self.assertIsNotNone(inventory)
            self.assertEqual(inventory.quantity, 10)
            self.assertEqual(inventory.available_balance, 9)  # 10 - 1

            # Edit inventory
            response = self.client.post(f'/edit_inventory/{inventory.id}', data={
                'item_type': 'carton',
                'quantity': 15,
                'broken_quantity': 2,
                'action': 'in',
                'date': '2023-01-02',
                'product_name': 'Updated Product',
                'size': '15cm x 25cm x 35cm'
            }, follow_redirects=True)
            self.assertIn(b'Updated Product', response.data)

            # Verify inventory was updated
            updated_inventory = Inventory.query.get(inventory.id)
            self.assertEqual(updated_inventory.item_type, 'carton')
            self.assertEqual(updated_inventory.available_balance, 13)  # 15 - 2

            # Delete inventory
            response = self.client.post(f'/delete_inventory/{inventory.id}', follow_redirects=True)
            self.assertNotIn(b'Updated Product', response.data)

            # Verify inventory was deleted
            deleted_inventory = Inventory.query.get(inventory.id)
            self.assertIsNone(deleted_inventory)

    def test_crud_user(self):
        with self.client:
            # Log in as admin
            self.client.post('/login', data=dict(username='admin', password='admin123'), follow_redirects=True)

            # Add user
            response = self.client.post('/add_user', data={
                'username': 'testuser',
                'password': 'testpass',
                'role': 'orders'
            }, follow_redirects=True)
            self.assertIn(b'testuser', response.data)

            # Verify user was added
            user = User.query.filter_by(username='testuser').first()
            self.assertIsNotNone(user)
            self.assertEqual(user.role, 'orders')

            # Edit user
            response = self.client.post(f'/edit_user/{user.id}', data={
                'username': 'updateduser',
                'password': 'updatedpass',
                'role': 'production'
            }, follow_redirects=True)
            self.assertIn(b'updateduser', response.data)

            # Verify user was updated
            updated_user = User.query.get(user.id)
            self.assertEqual(updated_user.username, 'updateduser')
            self.assertEqual(updated_user.role, 'production')

            # Delete user
            response = self.client.post(f'/delete_user/{user.id}', follow_redirects=True)
            self.assertNotIn(b'updateduser', response.data)

            # Verify user was deleted
            deleted_user = User.query.get(user.id)
            self.assertIsNone(deleted_user)

    def test_authentication_authorization(self):
        with self.client:
            # Test login with valid credentials
            response = self.client.post('/login', data=dict(username='admin', password='admin123'), follow_redirects=True)
            self.assertIn(b'Dashboard', response.data)  # Assuming dashboard has 'Dashboard'

            # Test access to admin page as admin
            response = self.client.get('/admin')
            self.assertIn(b'admin', response.data)

            # Test access to orders as orders user
            self.client.post('/login', data=dict(username='Ahmed', password='ahmed123'), follow_redirects=True)
            response = self.client.get('/orders')
            self.assertIn(b'Orders', response.data)  # Assuming orders page has 'Orders'

            # Test unauthorized access
            response = self.client.get('/admin')
            self.assertEqual(response.status_code, 302)  # Redirect to index

    def test_api_check_inventory_balance(self):
        with self.client:
            # Log in as inventory user
            self.client.post('/login', data=dict(username='Mohammed', password='mohammed123'), follow_redirects=True)

            # Add inventory
            self.client.post('/add_inventory', data={
                'item_type': 'box',
                'quantity': 10,
                'broken_quantity': 1,
                'action': 'in',
                'date': '2023-01-01',
                'product_name': 'Test Product',
                'size': '10cm x 20cm x 30cm'
            }, follow_redirects=True)

            # Test API
            response = self.client.get('/api/check_inventory_balance?product_name=Test Product&size=10cm x 20cm x 30cm&item_type=box')
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data['available_balance'], 9)  # 10 - 1

    def test_search_functionality(self):
        with self.client:
            # Log in as admin
            self.client.post('/login', data=dict(username='admin', password='admin123'), follow_redirects=True)

            # Add sample data
            self.client.post('/add_order', data={
                'details': 'Search Test Order',
                'receive_date': '2023-01-01',
                'product_name': 'Search Product',
                'size': 'Large',
                'quantity': 10
            }, follow_redirects=True)

            self.client.post('/add_production', data={
                'details': 'Search Test Production',
                'date': '2023-01-01',
                'product_name': 'Search Product',
                'size': '10cm x 20cm x 30cm',
                'quantity': 10,
                'broken_quantity': 1
            }, follow_redirects=True)

            self.client.post('/add_inventory', data={
                'item_type': 'box',
                'quantity': 10,
                'broken_quantity': 1,
                'action': 'in',
                'date': '2023-01-01',
                'product_name': 'Search Product',
                'size': '10cm x 20cm x 30cm'
            }, follow_redirects=True)

            # Test search
            response = self.client.get('/search?q=Search')
            self.assertIn(b'Search Product', response.data)

    def test_edge_cases(self):
        with self.client:
            # Log in as inventory user
            self.client.post('/login', data=dict(username='Mohammed', password='mohammed123'), follow_redirects=True)

            # Test insufficient balance
            response = self.client.post('/add_inventory', data={
                'item_type': 'box',
                'quantity': 10,
                'broken_quantity': 0,
                'action': 'in',
                'date': '2023-01-01',
                'product_name': 'Test Product',
                'size': '10cm x 20cm x 30cm'
            }, follow_redirects=True)

            # Try to out more than available
            response = self.client.post('/add_inventory', data={
                'item_type': 'box',
                'quantity': 15,
                'broken_quantity': 0,
                'action': 'out',
                'date': '2023-01-02',
                'product_name': 'Test Product',
                'size': '10cm x 20cm x 30cm'
            }, follow_redirects=True)
            self.assertIn(b'Insufficient balance', response.data)

            # Log in as orders user for order test
            self.client.post('/login', data=dict(username='Ahmed', password='ahmed123'), follow_redirects=True)

            # Test invalid date format in order
            response = self.client.post('/add_order', data={
                'details': 'Invalid Date',
                'receive_date': 'invalid-date',
                'product_name': 'Test',
                'size': 'Large',
                'quantity': 1
            }, follow_redirects=True)
            self.assertIn(b'Invalid receive date format', response.data)


if __name__ == '__main__':
    # Add sample users for the *application*, not tests
    with app.app_context():
        # Only add users if they don't already exist to prevent IntegrityError on app startup
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', password=generate_password_hash('admin123'), role='admin')
            db.session.add(admin)
        if not User.query.filter_by(username='Ahmed').first():
            ahmed = User(username='Ahmed', password=generate_password_hash('ahmed123'), role='orders')
            db.session.add(ahmed)
        if not User.query.filter_by(username='Ashraf').first():
            ashraf = User(username='Ashraf', password=generate_password_hash('ashraf123'), role='production')
            db.session.add(ashraf)
        if not User.query.filter_by(username='Mohammed').first():
            mohammed = User(username='Mohammed', password=generate_password_hash('mohammed123'), role='inventory')
            db.session.add(mohammed)
        # Add sample order if none exist
        if not Order.query.first():
            admin_user = User.query.filter_by(username='admin').first()
            if admin_user:
                sample_order = Order(
                    details='Sample Order Details',
                    order_type='in',
                    date=datetime.now(),
                    product_name='Sample Product',
                    size='10cm x 20cm x 30cm',
                    quantity=5,
                    available_balance=5,
                    user_id=admin_user.id
                )
                db.session.add(sample_order)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error during initial user creation: {e}") # Log the error
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
