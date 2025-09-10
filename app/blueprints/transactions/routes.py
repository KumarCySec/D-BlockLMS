"""
Transaction web routes for UI
"""
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.blueprints.transactions import bp
from app.models.transaction import Transaction
from app.models.inventory_item import InventoryItem
from app.utils.auth import role_required


@bp.route('/request')
@login_required
def request_item():
    """Show checkout request form"""
    item_id = request.args.get('item_id')
    if not item_id:
        flash('No item specified for checkout request.', 'error')
        return redirect(url_for('inventory.index'))
    
    # Verify item exists and is available
    item = InventoryItem.query.get_or_404(item_id)
    
    return render_template('transactions/request.html', item=item)


@bp.route('/history')
@login_required
def history():
    """Show user's transaction history"""
    return render_template('transactions/history.html')


@bp.route('/approval-dashboard')
@login_required
@role_required('Admin', 'Incharge', 'Volunteer')
def approval_dashboard():
    """Show approval dashboard for volunteers/staff"""
    return render_template('transactions/approval_dashboard.html')


@bp.route('/manage')
@login_required
@role_required('Admin', 'Incharge')
def manage():
    """Show transaction management interface for admin/incharge"""
    return render_template('transactions/manage.html')


@bp.route('/')
@login_required
def index():
    """Transaction index - redirect based on user role"""
    if current_user.has_role('Student'):
        return redirect(url_for('transactions.history'))
    else:
        return redirect(url_for('transactions.approval_dashboard'))