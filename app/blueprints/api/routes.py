"""
API routes
"""
from flask import jsonify
from app.blueprints.api import bp


@bp.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'D-Block Library Management System'})