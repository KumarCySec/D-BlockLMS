"""
API blueprint
"""
from flask import Blueprint

bp = Blueprint('api', __name__)

# Exempt API routes from CSRF protection
from app import csrf
csrf.exempt(bp)

from app.blueprints.api import routes, inventory