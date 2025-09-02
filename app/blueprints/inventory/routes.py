"""
Inventory web interface routes
"""
from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user
from app.blueprints.inventory import bp
from app.utils.auth import login_required_with_status, role_required


@bp.route('/')
@login_required_with_status
def index():
    """Inventory listing page"""
    return render_template('inventory/index.html')


@bp.route('/add-item')
@role_required('Admin', 'Incharge')
def add_item():
    """Add inventory item form"""
    return render_template('inventory/add_item.html')


@bp.route('/add-donor')
@role_required('Admin', 'Incharge')
def add_donor():
    """Add donor form"""
    return render_template('inventory/add_donor.html')


@bp.route('/item/<int:item_id>')
@login_required_with_status
def item_detail(item_id):
    """Item detail page"""
    # This will be implemented when we have the full item detail template
    return redirect(url_for('inventory.index'))


@bp.route('/donor/<int:donor_id>')
@login_required_with_status
def donor_detail(donor_id):
    """Donor detail page"""
    # This will be implemented when we have the donor detail template
    return redirect(url_for('inventory.index'))