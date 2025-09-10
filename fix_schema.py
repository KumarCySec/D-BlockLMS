#!/usr/bin/env python3
"""
Fix database schema by adding missing columns
"""
import os
import sys
sys.path.insert(0, os.path.abspath('.'))

from app import create_app, db
from sqlalchemy import text

def fix_schema():
    app = create_app()
    
    with app.app_context():
        try:
            # Add missing columns to inventory_item table
            db.session.execute(text("ALTER TABLE inventory_item ADD COLUMN status VARCHAR(10) DEFAULT 'AVAILABLE'"))
            db.session.execute(text("ALTER TABLE inventory_item ADD COLUMN isbn VARCHAR(20)"))
            db.session.commit()
            print("✓ Added missing columns to inventory_item table")
        except Exception as e:
            print(f"Note: Columns may already exist: {e}")
            db.session.rollback()

if __name__ == "__main__":
    fix_schema()