from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from .models import Order, Product, User, Transaction, Purchase, AccountStatus
from . import db, mail
from flask import current_app as app
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from flask_mail import Message
from .forms import FundUserBalanceForm

admin = Blueprint('admin', __name__, template_folder='templates/admin')


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/admin')
@login_required
def admin_index():
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('admin.index'))

    # Example data fetching for the admin dashboard
    users = User.query.all()
    transactions = Transaction.query.all()
    return render_template('admin/index.html', users=users, transactions=transactions)

@admin.route('/admin/dashboard')
@admin_required
def dashboard():
    try:
        # Get query parameters for filtering
        status_filter = request.args.get('status', 'all')
        date_filter = request.args.get('date', 'all')
        
        # Base query
        orders_query = Order.query

        # Apply status filter
        if status_filter != 'all':
            orders_query = orders_query.filter(Order.status == status_filter)

        # Apply date filter
        if date_filter == 'today':
            orders_query = orders_query.filter(
                db.func.date(Order.created_at) == db.func.date(datetime.utcnow())
            )
        elif date_filter == 'week':
            orders_query = orders_query.filter(
                Order.created_at >= datetime.utcnow() - timedelta(days=7)
            )

        # Get final results
        orders = orders_query.order_by(Order.created_at.desc()).all()
        products = Product.query.all()
        
        # Calculate statistics
        statistics = {
            'total_sales': sum(order.total_price for order in orders if order.payment_status == "Paid"),
            'pending_orders': len([order for order in orders if order.status == "Pending"]),
            'completed_orders': len([order for order in orders if order.status == "Completed"]),
            'total_products': len(products),
            'low_stock_products': len([product for product in products if product.stock < 10])
        }

        return render_template(
            'admin/dashboard.html',
            orders=orders,
            products=products,
            statistics=statistics,
            current_status=status_filter,
            current_date=date_filter
        )
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

@admin.route('/update-order-status/<int:order_id>', methods=['POST'])
@admin_required
def update_order_status(order_id):
    try:
        order = Order.query.get_or_404(order_id)
        new_status = request.form.get('status')
        
        if new_status not in ['Pending', 'Processing', 'Completed', 'Cancelled']:
            flash('Invalid status provided', 'error')
            return redirect(url_for('admin.dashboard'))
        
        order.status = new_status
        order.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash(f'Order {order_id} status updated to {new_status}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating order: {str(e)}', 'error')
    
    return redirect(url_for('admin.dashboard'))




# Admin-related routes for viewing users, crediting users, etc.
@admin.route('/users')
@login_required
def view_users():
    if not current_user.is_admin:
        flash('Access denied!', 'danger')
        return redirect(url_for('main.index'))

    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin.route('/credit/<int:user_id>', methods=['POST'])
@login_required
def credit_user(user_id):
    if not current_user.is_admin:
        flash('Access denied!', 'danger')
        return redirect(url_for('main.index'))

    user = User.query.get(user_id)
    if user:
        amount = request.form.get('amount', type=int)
        if amount and amount > 0:
            user.balance += amount
            db.session.commit()
            flash(f'Credited ${amount} to {user.name}', 'success')
        else:
            flash('Invalid amount!', 'danger')
    else:
        flash('User not found!', 'danger')
    return redirect(url_for('admin.view_users'))

@admin.route('/create_admin', methods=['GET', 'POST'])
@login_required
def create_admin():
    if not current_user.is_admin:
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        new_admin = User(email=email, name=name, password=hashed_password, is_admin=True)
        db.session.add(new_admin)
        db.session.commit()
        flash('Admin account created successfully!', 'success')
        return redirect(url_for('admin.create_admin'))

    return render_template('create_admin.html')




@admin.route('/admin/products', methods=['GET'])
def product_list():
    # Query all products from the database
    products = Product.query.all()
    return render_template('admin/products.html', products=products)


@admin.route('/admin/product/<int:product_id>/edit', methods=['GET', 'POST'])
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        product.name = request.form['name']
        product.description = request.form['description']
        product.price = float(request.form['price'])
        product.category = request.form['category']
        product.stock = int(request.form['stock'])
        product.is_active = 'is_active' in request.form
        product.login = request.form['login']  # Adding login details

        db.session.commit()
        flash('Product updated successfully.')
        return redirect(url_for('admin.product_list'))
    
    return render_template('admin/edit_product.html', product=product)

@admin.route('/admin/product/<int:product_id>/delete', methods=['POST'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully.')
    return redirect(url_for('admin.product_list'))

@admin.route('/add_product', methods=['GET', 'POST'])
@login_required  # Ensure the user is logged in
def add_product():
    if request.method == 'POST':
        # Retrieve form data
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        category = request.form['category']
        stock = int(request.form['stock'])
        login = request.form.get('login', '')  # Optional field
        is_active = 'is_active' in request.form  # Checkbox for active status

        # Create a new Product instance
        new_product = Product(
            name=name,
            description=description,
            price=price,
            category=category,
            stock=stock,
            login=login,
            is_active=is_active
        )

        # Add the product to the database
        db.session.add(new_product)
        db.session.commit()

        flash('Product added successfully!', 'success')
        return redirect(url_for('admin.product_list'))  # Redirect to the product list page

    return render_template('admin/add_product.html')


@admin.route('/users')
def users():
    # Fetch all users from the database
    users = User.query.all()
    return render_template('users.html', users=users)


@admin.route('/user/<int:user_id>/preview')
def user_preview(user_id):
    # Retrieve the user by their ID or return 404 if not found
    user = User.query.get_or_404(user_id)
    
    # Retrieve the user's transactions, purchases, and orders
    transactions = Transaction.query.filter_by(user_id=user.id).all()
    purchases = Purchase.query.filter_by(user_id=user.id).all()
    orders = Order.query.filter_by(user_id=user.id).all()
    
    # Return the preview page with user details
    return render_template('admin/user_preview.html', user=user, transactions=transactions, purchases=purchases, orders=orders)
       

@admin.route('/user/<int:user_id>/fund', methods=['POST'])
def fund_user_balance(user_id):
    user = User.query.get_or_404(user_id)
    amount = float(request.form['amount'])
    
    # Add the amount to the user's balance
    user.balance += amount
    db.session.commit()
    
    return redirect(url_for('admin/user_preview', user_id=user.id))       


@admin.route('/admin/update_status/<int:user_id>/<status>', methods=['GET', 'POST'])
@login_required
def update_status(user_id, status):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('admin.users'))

    # Validating the status
    if status not in ['Active', 'Suspended', 'Blocked']:
        flash('Invalid status.', 'danger')
        return redirect(url_for('admin.users'))

    # Update the user's account status
    user = User.query.get_or_404(user_id)
    user.account_status = status
    db.session.commit()

    flash(f'User account status updated to {status}.', 'success')
    return redirect(url_for('admin.users'))




# Route to fund user balance
@admin.route('/fund_user', methods=['GET', 'POST'])
@login_required
def fund_user():
    if not current_user.is_admin:
        flash("You do not have permission to perform this action.", 'danger')
        return redirect(url_for('main.index'))  # Or any other page for non-admin users

    form = FundUserBalanceForm()

    # Populate the user dropdown
    form.user_id.choices = [(user.id, user.email) for user in User.query.all()]

    if form.validate_on_submit():
        user = User.query.get(form.user_id.data)
        amount = form.amount.data
        action = form.action.data

        # Update the user's balance based on the action
        if action == 'increase':
            user.balance += amount
        elif action == 'decrease':
            user.balance -= amount

        # Commit the changes to the database
        db.session.commit()

        # Send email notification to the user
        send_email_notification(user.email, amount, action)

        flash(f'User {user.email}\'s balance has been successfully updated.', 'success')
        return redirect(url_for('admin.users', user_id=user.id))  # Redirect to user view page

    return render_template('fund_user.html', form=form)


def send_email_notification(user_email, amount, action):
    """ Sends an email to the user about the balance update """
    subject = 'Your account balance has been updated'
    if action == 'increase':
        body = f'Your account has been credited with ${amount}.'
    else:
        body = f'Your account has been debited ${amount}.'

    msg = Message(subject=subject,
                  recipients=[user_email],
                  body=body)
    try:
        mail.send(msg)
    except Exception as e:
        app.logger.error(f"Error sending email: {e}")


