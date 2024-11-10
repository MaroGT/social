from flask import Blueprint, render_template, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from .forms import ProfileForm
from .forms import (
    ProfileSettingsForm, 
    FundAccountForm, 
    ChangePasswordForm,
    UpdateNotificationSettingsForm
)

from .models import db, User, Product, Order
from .utils import send_email
import json
from . import db  # Add this import for database operations


user = Blueprint('user', __name__)

@user.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    # Calculate user stats and summary
    total_orders = Orders.query.filter_by(user_id=current_user.id).count()
    total_spent = sum(order.total_amount for order in current_user.orders)
    active_orders = Orders.query.filter_by(user_id=current_user.id, status='active').count()

    # Get recent orders (last 5)
    recent_orders = (Orders.query
                    .filter_by(user_id=current_user.id)
                    .order_by(Orders.created_at.desc())
                    .limit(5)
                    .all())
    
    # Get account activity (last 10 transactions)
    recent_transactions = (Transaction.query
                         .filter_by(user_id=current_user.id)
                         .order_by(Transaction.timestamp.desc())
                         .limit(10)
                         .all())
    
    # Account statistics
    account_stats = {
        'total_orders': total_orders,
        'total_spent': total_spent,
        'active_orders': active_orders,
        'account_balance': current_user.balance,
        'join_date': current_user.created_at,
        'last_login': current_user.last_login
    }
    
    return render_template(
        'dashboard.html',
        stats=account_stats,
        recent_orders=recent_orders,
        recent_transactions=recent_transactions
    )


@user.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()

    if form.validate_on_submit():
        # Update user information
        current_user.name = form.name.data
        current_user.email = form.email.data

        if form.password.data:
            current_user.set_password(form.password.data)
        
        db.session.commit()
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('user.profile'))

    # Pre-fill form with current user information
    form.name.data = current_user.name
    form.email.data = current_user.email
    return render_template('profile.html', form=form)


@user.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    # Confirm the user wants to delete their account
    db.session.delete(current_user)
    db.session.commit()
    
    flash('Your account has been deleted successfully.', 'success')
    return redirect(url_for('auth.logout'))

