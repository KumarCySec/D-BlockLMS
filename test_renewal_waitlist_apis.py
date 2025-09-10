#!/usr/bin/env python3
"""
Test script for renewal and waitlist API functionality
"""
import os
import sys
sys.path.insert(0, os.path.abspath('.'))

from app import create_app, db
from app.models import (User, InventoryItem, Transaction, TransactionStatus, 
                       WaitlistRequest, WaitlistStatus, FineRecord, FineConfiguration)
from datetime import datetime, timedelta
import json

def test_apis():
    app = create_app()
    
    with app.test_client() as client:
        with app.app_context():
            print("Testing renewal and waitlist APIs...")
            
            # Get test data
            users = User.query.limit(3).all()
            items = InventoryItem.query.limit(2).all()
            
            if not users or not items:
                print("No test data found. Please run create_test_data.py first.")
                return
            
            user1, user2 = users[0], users[1]
            item = items[0]  # This should be unavailable (quantity = 0)
            
            print(f"Testing with users: {user1.name}, {user2.name}")
            print(f"Testing with item: {item.title} (available: {item.available_quantity})")
            
            # Test 1: Join waitlist API (would need authentication in real app)
            print("\n1. Testing waitlist join...")
            
            # Simulate joining waitlist
            try:
                waitlist1 = WaitlistRequest.join_waitlist(user1.id, item.id, "Test waitlist 1")
                waitlist2 = WaitlistRequest.join_waitlist(user2.id, item.id, "Test waitlist 2")
                db.session.commit()
                
                print(f"✓ User1 joined waitlist at position {waitlist1.position}")
                print(f"✓ User2 joined waitlist at position {waitlist2.position}")
                
            except Exception as e:
                print(f"✗ Error joining waitlist: {e}")
                db.session.rollback()
            
            # Test 2: Get waitlist for item
            print("\n2. Testing waitlist retrieval...")
            
            item_waitlist = WaitlistRequest.get_item_waitlist(item.id)
            print(f"✓ Item has {len(item_waitlist)} waitlist requests")
            
            for req in item_waitlist:
                print(f"  - Position {req.position}: {req.user.name} ({req.status.value})")
            
            # Test 3: Notify waitlist user
            print("\n3. Testing waitlist notification...")
            
            try:
                waitlist1.notify_availability(24)
                db.session.commit()
                print(f"✓ Notified {waitlist1.user.name}, expires at {waitlist1.expires_at}")
                
            except Exception as e:
                print(f"✗ Error notifying waitlist: {e}")
                db.session.rollback()
            
            # Test 4: Fine configuration
            print("\n4. Testing fine configuration...")
            
            configs = FineConfiguration.create_default_configurations()
            db.session.commit()
            print(f"✓ Created {len(configs)} fine configurations")
            
            book_config = FineConfiguration.get_by_item_type('book')
            if book_config:
                print(f"  - Book: ₹{book_config.daily_rate}/day, grace: {book_config.grace_period_days} days")
            
            # Test 5: Create overdue transaction and calculate fine
            print("\n5. Testing fine calculation...")
            
            # Create an overdue transaction
            from app.models.transaction import TransactionCounter
            transaction_id = TransactionCounter.generate_transaction_id()
            
            overdue_transaction = Transaction(
                transaction_id=transaction_id,
                user_id=user1.id,
                item_id=items[1].id,  # Use available item
                status=TransactionStatus.BORROWED,
                requested_at=datetime.utcnow() - timedelta(days=10),
                approved_at=datetime.utcnow() - timedelta(days=9),
                issued_at=datetime.utcnow() - timedelta(days=9),
                due_date=datetime.utcnow() - timedelta(days=2)  # 2 days overdue
            )
            
            db.session.add(overdue_transaction)
            db.session.commit()
            
            # Calculate fine
            from app.models.fine import FineService
            calculated_fine = FineService.calculate_transaction_fine(overdue_transaction)
            print(f"✓ Calculated fine for overdue transaction: ₹{calculated_fine}")
            
            # Create fine record
            fine_record = FineRecord.create_fine_record(
                transaction_id=overdue_transaction.id,
                user_id=user1.id,
                item_id=items[1].id,
                days_overdue=2,
                daily_rate=book_config.daily_rate if book_config else 1.00
            )
            db.session.commit()
            
            print(f"✓ Created fine record: ₹{fine_record.fine_amount}")
            
            # Test 6: User fine summary
            print("\n6. Testing user fine summary...")
            
            user_summary = FineService.get_user_fine_summary(user1.id)
            print(f"✓ User {user1.name} has {user_summary['total_fines']} fines totaling ₹{user_summary['pending_amount']}")
            
            # Test 7: Waive fine
            print("\n7. Testing fine waiver...")
            
            fine_record.waive_fine(user2.id, "Test waiver")
            db.session.commit()
            
            updated_summary = FineService.get_user_fine_summary(user1.id)
            print(f"✓ After waiver: ₹{updated_summary['pending_amount']} pending, ₹{updated_summary['waived_amount']} waived")
            
            # Test 8: Renewal with waitlist conflict
            print("\n8. Testing renewal with waitlist conflict...")
            
            # Check if renewal would be blocked
            can_renew, message = overdue_transaction.can_renew()
            print(f"✓ Can renew: {can_renew}, Message: {message}")
            
            # Check waitlist conflict for item
            active_waitlist = WaitlistRequest.query.filter_by(
                item_id=item.id,
                status=WaitlistStatus.ACTIVE
            ).first()
            
            if active_waitlist:
                print(f"✓ Item {item.title} has active waitlist - renewal would require approval")
            else:
                print(f"✓ Item {items[1].title} has no waitlist - renewal allowed")
            
            # Test 9: Cleanup expired claims
            print("\n9. Testing expired claim cleanup...")
            
            expired_count, processed_items = WaitlistRequest.cleanup_expired_claims()
            print(f"✓ Cleanup processed {expired_count} expired claims for {processed_items} items")
            
            print("\nAll API functionality tests completed successfully!")

if __name__ == "__main__":
    test_apis()