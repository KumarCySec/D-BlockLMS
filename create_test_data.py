#!/usr/bin/env python3
"""
Create test data for waitlist functionality
"""
import os
import sys
sys.path.insert(0, os.path.abspath('.'))

from app import create_app, db
from app.models import User, Role, Department, Donor, InventoryItem, ItemType, ItemStatus
from app.models.user import UserStatus
from datetime import datetime, date

def create_test_data():
    app = create_app()
    
    with app.app_context():
        # Create departments
        dept_cse = Department(name="Computer Science Engineering", code="CSE", description="Computer Science Engineering")
        dept_ece = Department(name="Electronics and Communication Engineering", code="ECE", description="Electronics and Communication Engineering")
        db.session.add_all([dept_cse, dept_ece])
        db.session.commit()
        
        # Create roles
        role_student = Role(name="Student", description="Student role")
        role_volunteer = Role(name="Volunteer", description="Volunteer role")
        role_admin = Role(name="Admin", description="Admin role")
        db.session.add_all([role_student, role_volunteer, role_admin])
        db.session.commit()
        
        # Create users
        user1 = User.create_user(
            name="Alice Johnson",
            roll_number="CSE001",
            branch="CSE",
            batch="2024",
            phone="9876543210",
            email="alice@example.com",
            password="password123",
            department_id=dept_cse.id
        )
        user1.status = UserStatus.ACTIVE
        user1.roles.append(role_student)
        
        user2 = User.create_user(
            name="Bob Smith",
            roll_number="ECE001",
            branch="ECE",
            batch="2024",
            phone="9876543211",
            email="bob@example.com",
            password="password123",
            department_id=dept_ece.id
        )
        user2.status = UserStatus.ACTIVE
        user2.roles.append(role_student)
        
        user3 = User.create_user(
            name="Carol Admin",
            roll_number="ADM001",
            branch="CSE",
            batch="2023",
            phone="9876543212",
            email="carol@example.com",
            password="password123",
            department_id=dept_cse.id
        )
        user3.status = UserStatus.ACTIVE
        user3.roles.append(role_admin)
        
        db.session.add_all([user1, user2, user3])
        db.session.commit()
        
        # Create donors
        donor1 = Donor(
            name="Dr. Sarah Wilson",
            branch="CSE",
            batch="2010",
            address="123 Tech Street, Silicon Valley",
            phone="9876543213",
            email="sarah.wilson@alumni.com",
            notes="Distinguished alumna, frequent donor"
        )
        
        donor2 = Donor(
            name="Mr. John Davis",
            branch="ECE",
            batch="2012",
            address="456 Innovation Ave, Tech City",
            phone="9876543214",
            email="john.davis@alumni.com",
            notes="Tech entrepreneur, donated laptops"
        )
        
        db.session.add_all([donor1, donor2])
        db.session.commit()
        
        # Create inventory items
        item1 = InventoryItem(
            item_type=ItemType.BOOK,
            status=ItemStatus.AVAILABLE,
            title="Introduction to Algorithms",
            authors="Thomas H. Cormen, Charles E. Leiserson",
            isbn="978-0262033848",
            language="English",
            published_date=date(2009, 7, 31),
            donor_id=donor1.id,
            date_of_donation=date(2024, 1, 15),
            total_quantity=2,
            available_quantity=0,  # Make unavailable to test waitlist
            department_id=dept_cse.id,
            description="Comprehensive guide to algorithms and data structures"
        )
        
        item2 = InventoryItem(
            item_type=ItemType.LAPTOP,
            status=ItemStatus.AVAILABLE,
            title="Dell Inspiron 15 3000",
            authors="Dell Inc.",
            language="English",
            donor_id=donor2.id,
            date_of_donation=date(2024, 2, 10),
            total_quantity=1,
            available_quantity=1,
            department_id=dept_ece.id,
            description="15.6-inch laptop for programming and development"
        )
        
        item3 = InventoryItem(
            item_type=ItemType.BOOK,
            status=ItemStatus.AVAILABLE,
            title="Digital Signal Processing",
            authors="Alan V. Oppenheim, Ronald W. Schafer",
            isbn="978-0131988422",
            language="English",
            published_date=date(2010, 8, 28),
            donor_id=donor2.id,
            date_of_donation=date(2024, 1, 20),
            total_quantity=1,
            available_quantity=0,  # Make unavailable to test waitlist
            department_id=dept_ece.id,
            description="Fundamental concepts in digital signal processing"
        )
        
        db.session.add_all([item1, item2, item3])
        db.session.commit()
        
        print("✓ Created test data:")
        print(f"  - {Department.query.count()} departments")
        print(f"  - {Role.query.count()} roles")
        print(f"  - {User.query.count()} users")
        print(f"  - {Donor.query.count()} donors")
        print(f"  - {InventoryItem.query.count()} inventory items")
        print("  - 2 items are unavailable for waitlist testing")

if __name__ == "__main__":
    create_test_data()