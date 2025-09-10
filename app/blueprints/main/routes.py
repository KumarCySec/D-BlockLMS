"""
Main application routes
"""
from flask import render_template
from app.blueprints.main import bp
from app.utils.auth import login_required_with_status


@bp.route('/')
def index():
    """Home page"""
    return render_template('index.html')


@bp.route('/dashboard')
@login_required_with_status
def dashboard():
    """User dashboard"""
    return render_template('dashboard.html')


@bp.route('/fines')
@login_required_with_status
def fines():
    """User fines page"""
    return render_template('fines.html')