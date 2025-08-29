"""
Main application routes
"""
from flask import render_template
from app.blueprints.main import bp


@bp.route('/')
def index():
    """Home page"""
    return render_template('index.html')


@bp.route('/dashboard')
def dashboard():
    """User dashboard"""
    return render_template('dashboard.html')