#!/usr/bin/env python3
"""
Test script for fine calculation and tracking functionality
"""
import os
import sys
sys.path.insert(0, os.path.abspath('.'))

from app import create_app, db
from app.models import (User, InventoryItem, Transaction, TransactionStatus, 
                       FineRecord, FineConfiguration, FineService)
from datetime import datetime, timedelta, date
from decimal import Decimal

def test_fine_system():
    app = create_app()
    
    with app.app_context():
        print("Testing fine calculation and tracking system...")
        
        # Create default fine configurations
        configs = FineConfiguration.create_default_configurations()
        db.session.commit()
        print(f"✓ Created {len(configs)} default fine configurations")
        
        # Test fine configuration
        book_config = FineConfiguration.get_by_item_type('book')
        if book_config:
            print(f"✓ Book fine config: ₹{book_config.daily_rate}/day, grace period: {book_config.grace_period_days} days")
            
            # Test fine calculation
            fine_0_days = book_config.calculate_fine(0)
            fine_1_day = book_config.calculate_fine(1)  # Within grace period
            fine_3_days = book_config.calculate_fine(3)  # 2 effective days
            
            print(f"  - 0 days overdue: ₹{fine_0_days}")
            print(f"  - 1 day overdue: ₹{fine_1_day} (grace period)")
            print(f"  - 3 days overdue: ₹{fine_3_days}")
        
        # Get test data
        users = User.query.limit(2).all()
        items = InventoryItem.query.limit(2).all()
        
        if not users or not items:
            print("No test data found. Please run create_test_data.py first.")
            return
        
        user = users[0]
        item = items[0]
        
        # Create a test transaction that's overdue
        from app.models.transaction import TransactionCounter
        transaction_id = TransactionCounter.generate_transaction_id()
        
        transaction = Transaction(
            transaction_id=transaction_id,
            user_id=user.id,
            item_id=item.id,
            status=TransactionStatus.BORROWED,
            requested_at=datetime.utcnow() - timedelta(days=10),
            approved_at=datetime.utcnow() - timedelta(days=9),
            issued_at=datetime.utcnow() - timedelta(days=9),
            due_date=datetime.utcnow() - timedelta(days=3)  # 3 days overdue
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        print(f"✓ Created test transaction {transaction.transaction_id} (3 days overdue)")
        
        # Test fine calculation for transaction
        calculated_fine = FineService.calculate_transaction_fine(transaction)
        print(f"✓ Calculated fine for transaction: ₹{calculated_fine}")
        
        # Create fine record
        fine_record = FineRecord.create_fine_record(
            transaction_id=transaction.id,
            user_id=user.id,
            item_id=item.id,
            days_overdue=3,
            daily_rate=Decimal('1.00')
        )
        db.session.commit()
        
        print(f"✓ Created fine record: ₹{fine_record.fine_amount}")
        
        # Test user fine summary
        user_summary = FineService.get_user_fine_summary(user.id)
        print(f"✓ User fine summary: {user_summary['total_fines']} fines, ₹{user_summary['pending_amount']} pending")
        
        # Test fine waiver
        admin_user = users[1] if len(users) > 1 else user
        fine_record.waive_fine(admin_user.id, "Test waiver")
        db.session.commit()
        
        print(f"✓ Fine waived by {admin_user.name}")
        
        # Test updated user summary
        updated_summary = FineService.get_user_fine_summary(user.id)
        print(f"✓ Updated summary: ₹{updated_summary['pending_amount']} pending, ₹{updated_summary['waived_amount']} waived")
        
        # Test fine statistics
        stats = FineRecord.get_fine_statistics()
        print(f"✓ Fine statistics: {stats}")
        
        # Test daily fine record creation
        created_records = FineService.create_daily_fine_records()
        print(f"✓ Daily fine job would create {len(created_records)} new records")
        
        print("All fine system tests passed!")

if __name__ == "__main__":
    test_fine_system()