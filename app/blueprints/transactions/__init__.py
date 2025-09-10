"""
Transactions blueprint
"""
from flask import Blueprint

bp = Blueprint('transactions', __name__)

from app.blueprints.transactions import routes