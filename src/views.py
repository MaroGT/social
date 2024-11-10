from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from .models import db, User, Product, Notification, Order, OrderItem
from flask_login import current_user, login_required
import stripe
from .utils import send_email

import json


main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    products = Product.query.all()
    return render_template('home.html', products=products)

@main_bp.route('/notifications')
def notifications():
    user = current_user  # Assuming you're using Flask-Login for authentication
    notifications = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).all()
    return render_template('notifications.html', notifications=notifications)

@main_bp.route('/mark-as-read/<int:notification_id>')
def mark_as_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id == current_user.id:
        notification.is_read = True
        db.session.commit()
        flash("Notification marked as read", "success")
    else:
        flash("You cannot mark this notification as read.", "danger")
    return redirect(url_for('main.notifications'))





@main_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        cart = session.get('cart', {})
        if not cart:
            flash("Your cart is empty.")
            return redirect(url_for('main.cart'))
        
        total_price = sum(item['price'] * item['quantity'] for item in cart.values())
        user_id = session.get('user_id')
        
        if user_id:
            new_order = Order(user_id=user_id, total_price=total_price, status="Pending")
            db.session.add(new_order)
            db.session.commit()
            
            # Send order confirmation email
            user = User.query.get(user_id)
            send_email(
                subject="Order Confirmation",
                recipients=[user.email],
                body=f"Thank you for your order #{new_order.id}! Total: ${total_price}"
            )
            
            for product_id, item in cart.items():
                order_item = OrderItem(
                    order_id=new_order.id,
                    product_id=product_id,
                    quantity=item['quantity'],
                    price=item['price']
                )
                db.session.add(order_item)
            
            db.session.commit()
            session.pop('cart', None)
            flash("Order placed successfully!")
            return redirect(url_for('main.order_history'))
        else:
            flash("Please log in to complete the purchase.")
            return redirect(url_for('auth.login'))

    cart = session.get('cart', {})
    total = sum(item['price'] * item['quantity'] for item in cart.values())
    return render_template('checkout.html', cart=cart, total=total)



@main_bp.route('/order_history')
def order_history():
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to view your order history.")
        return redirect(url_for('auth.login'))
    
    orders = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()
    return render_template('order_history.html', orders=orders)


@main_bp.route('/order/<int:order_id>')
def order_details(order_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to view order details.")
        return redirect(url_for('auth.login'))
    
    order = Order.query.filter_by(id=order_id, user_id=user_id).first_or_404()
    return render_template('order_details.html', order=order)


@main_bp.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    cart = session.get('cart', {})
    if not cart:
        flash("Your cart is empty.")
        return redirect(url_for('main.cart'))

    line_items = [
        {
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': item['name'],
                },
                'unit_amount': int(item['price'] * 100),  # Stripe uses cents
            },
            'quantity': item['quantity'],
        }
        for item in cart.values()
    ]

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=url_for('main.payment_success', _external=True),
            cancel_url=url_for('main.payment_cancel', _external=True),
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        flash(f"Payment failed: {e}")
        return redirect(url_for('main.cart'))


@main_bp.route('/payment-success')
def payment_success():
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to view your order history.")
        return redirect(url_for('auth.login'))

    order = Order.query.filter_by(user_id=user_id, status="Pending").first()
    if order:
        order.status = "Completed"
        order.payment_status = "Paid"
        db.session.commit()

        # Send payment confirmation email
        user = User.query.get(user_id)
        send_email(
            subject="Payment Confirmation",
            recipients=[user.email],
            body=f"Your payment for order #{order.id} has been successfully processed."
        )
    
    session.pop('cart', None)
    flash("Payment successful! Thank you for your purchase.")
    return redirect(url_for('main.order_history'))


@main_bp.route('/payment-cancel')
def payment_cancel():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        send_email(
            subject="Payment Canceled",
            recipients=[user.email],
            body="Your payment has been canceled. You can return to the store to try again."
        )
    
    flash("Payment canceled. You can try again.")
    return redirect(url_for('main.cart'))


@main_bp.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
        )
    except ValueError as e:
        # Invalid payload
        print("Invalid payload")
        return jsonify(success=False), 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print("Invalid signature")
        return jsonify(success=False), 400

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # Update order status to completed in the database
        order_id = session.get('client_reference_id')
        order = Order.query.get(order_id)
        if order:
            order.payment_status = 'Paid'
            db.session.commit()

               # Create a notification for the user
            notification = Notification(
                user_id=order.user_id,
                message=f"Your payment for {order.product_name} was successful!",
            )
            db.session.add(notification)
            db.session.commit()


    return jsonify(success=True)
