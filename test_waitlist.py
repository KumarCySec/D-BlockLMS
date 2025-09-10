#!/usr/bin/env python3
"""
Test script for waitlist functionality
"""
import os
import sys
sys.path.insert(0, os.path.abspath('.'))

from app import create_app, db
from app.models import User, InventoryItem, WaitlistRequest, WaitlistStatus
from datetime import datetime

def test_waitlist():
    app = create_app()
    
    with app.app_context():
        # Test basic waitlist functionality
        print("Testing waitlist functionality...")
        
        # Check if we have any users and items
        users = User.query.limit(3).all()
        items = InventoryItem.query.limit(2).all()
        
        if not users:
            print("No users found in database")
            return
        
        if not items:
            print("No inventory items found in database")
            return
        
        print(f"Found {len(users)} users and {len(items)} items")
        
        # Test joining waitlist
        user = users[0]
        item = items[0]
        
        print(f"Testing waitlist for user {user.name} and item {item.title}")
        
        try:
            # Join waitlist
            waitlist_request = WaitlistRequest.join_waitlist(
                user_id=user.id,
                item_id=item.id,
                notes="Test waitlist request"
            )
            db.session.commit()
            
            print(f"✓ Successfully joined waitlist at position {waitlist_request.position}")
            
            # Test getting waitlist for item
            item_waitlist = WaitlistRequest.get_item_waitlist(item.id)
            print(f"✓ Item waitlist has {len(item_waitlist)} requests")
            
            # Test getting user waitlist
            user_waitlist = WaitlistRequest.get_user_waitlist(user.id)
            print(f"✓ User has {len(user_waitlist)} waitlist requests")
            
            # Test notification
            waitlist_request.notify_availability()
            db.session.commit()
            print(f"✓ Notification sent, status: {waitlist_request.status.value}")
            
            # Test statistics
            stats = WaitlistRequest.get_waitlist_statistics(item.id)
            print(f"✓ Waitlist statistics: {stats}")
            
            print("All waitlist tests passed!")
            
        except Exception as e:
            print(f"✗ Error testing waitlist: {e}")
            db.session.rollback()

if __name__ == "__main__":
    test_waitlist()