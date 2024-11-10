from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from flask_login import current_user, login_required
from .models import Product, db, Purchase, Transaction
from datetime import datetime
# src/routes.py or wherever the checkout route is defined
from .utils import send_purchase_details

from decimal import Decimal


market = Blueprint('market', __name__)  # Ensure this is 'market'


# Display products on the marketplace
from datetime import datetime

@market.route('/marketplace')
def marketplace():
    # Fetch all active products from the database
    products = Product.query.filter_by(is_active=True).all()

    # Calculate the age in years for each product
    for product in products:
        time_diff = datetime.utcnow() - product.created_at
        years = time_diff.days / 365.25  # Divide by 365.25 for a more accurate year fraction

        # Format `product.age` to two decimal places
        product.age = round(years, 2)  # e.g., 2.57 years

    return render_template('marketplace.html', products=products)




# Route for product details (view more info)
@market.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    form = AddToCartForm()
    form.product_id.data = product_id  # Set the product_id in the form

    if form.validate_on_submit():
        quantity = form.quantity.data

    # Calculate the age of the product in years
    time_diff = datetime.utcnow() - product.created_at
    years = time_diff.days / 365.25  # Dividing by 365.25 to account for leap years
    product.age = round(years, 2)  # Store the age with two decimal precision

    return render_template('product_detail.html', product=product, form=form)




@market.route('/checkout', methods=['POST'])
def checkout():
    cart_ids = session.get('cart', [])
    products_in_cart = Product.query.filter(Product.id.in_(cart_ids)).all()

    total_amount = sum(float(product.price) for product in products_in_cart)

    if current_user.balance < total_amount:
        flash('Insufficient funds. Please add more coins to your account.', 'danger')
        return redirect(url_for('market.marketplace'))

    # Deduct total amount from user balance
    current_user.balance -= total_amount
    db.session.commit()

    # Create transaction record
    transaction = Transaction(
        user_id=current_user.id,
        amount=str(total_amount),
        type='order_payment',
        payment_method='coins',
        status='completed'
    )
    db.session.add(transaction)
    db.session.commit()

    # Update product stock and deactivate if necessary
    for product in products_in_cart:
        product.stock -= 1
        if product.stock == 0:
            product.is_active = False
        db.session.commit()

        # Send purchase details (you can modify this based on your requirements)
        send_purchase_details(current_user.email, product)

    session['cart'] = []

    flash('Checkout successful. Your products have been purchased.', 'success')
    return redirect(url_for('market.marketplace'))



from .models import Product, Purchase, Transaction, TransactionType, db

from .forms import AddToCartForm

from datetime import datetime

@market.route('/transaction_history')
@login_required
def transaction_history():
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    return render_template('transaction_history.html', transactions=transactions)

@market.route('/my_purchases')
@login_required
def my_purchases():
    purchases = Purchase.query.filter_by(user_id=current_user.id).all()
    return render_template('my_purchases.html', purchases=purchases)



@market.route('/quick_buy/<int:product_id>', methods=['POST'])
@login_required
def quick_buy(product_id):
    product = Product.query.get_or_404(product_id)

    if product.stock <= 0 or not product.is_active:
        flash('Product is out of stock or unavailable.', 'danger')
        return redirect(url_for('market.marketplace'))

    if current_user.balance < product.price:
        flash('Insufficient balance to complete this purchase.', 'danger')
        return redirect(url_for('market.marketplace'))

    # Deduct balance and update product stock
    current_user.balance -= product.price
    product.stock -= 1
    db.session.commit()

    # Record the purchase
    purchase = Purchase(user_id=current_user.id, product_id=product.id, price=product.price)
    db.session.add(purchase)
    db.session.commit()

    # Record the transaction
    transaction = Transaction(user_id=current_user.id, amount=product.price, type=TransactionType.PURCHASE)
    db.session.add(transaction)
    db.session.commit()

    flash(f'Successfully purchased {product.name}.', 'success')
    return redirect(url_for('market.my_purchases'))

