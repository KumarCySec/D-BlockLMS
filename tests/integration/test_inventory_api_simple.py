"""
Simplified integration tests for inventory API endpoints
"""
import pytest
import json
from datetime import date
from app.models.user import User, UserStatus
from app.models.role import Role
from app.models.department import Department
from app.models.donor import Donor
from app.models.inventory_item import InventoryItem, ItemType
from app import db


class TestInventoryAPISimple:
    """Simplified test inventory API endpoints"""
    
    def test_get_inventory_unauthorized(self, client):
        """Test inventory endpoint without authentication"""
        response = client.get('/api/inventory')
        assert response.status_code == 302  # Redirect to login
    
    def test_get_inventory_success(self, app, client):
        """Test successful inventory retrieval"""
        with app.app_context():
            # Create user
            user = User.create_user(
                name="Test Student",
                roll_number="STU001",
                branch="CSE",
                batch="2021-2025",
                phone="9876543210",
                email="student@test.com",
                password="password123"
            )
            user.status = UserStatus.ACTIVE
            
            role = Role.get_by_name('Student')
            user.roles.append(role)
            
            # Create donor and item
            donor = Donor(
                name="Test Donor",
                branch="CSE",
                batch="2020-2024"
            )
            
            db.session.add_all([user, donor])
            db.session.commit()
            
            item = InventoryItem(
                item_type=ItemType.BOOK,
                title="Test Book",
                authors="Test Author",
                donor_id=donor.id,
                total_quantity=10,
                available_quantity=8,
                date_of_donation=date.today()
            )
            
            db.session.add(item)
            db.session.commit()
            
            # Login user
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
            
            # Test API
            response = client.get('/api/inventory')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'items' in data['data']
            assert 'pagination' in data['data']
            assert 'filters' in data['data']
    
    def test_create_inventory_item_success(self, app, client):
        """Test creating inventory item as Admin"""
        with app.app_context():
            # Create admin user
            user = User.create_user(
                name="Test Admin",
                roll_number="ADMIN001",
                branch="CSE",
                batch="2021-2025",
                phone="9876543210",
                email="admin@test.com",
                password="password123"
            )
            user.status = UserStatus.ACTIVE
            
            role = Role.get_by_name('Admin')
            user.roles.append(role)
            
            # Create donor
            donor = Donor(
                name="Test Donor",
                branch="CSE",
                batch="2020-2024"
            )
            
            db.session.add_all([user, donor])
            db.session.commit()
            
            # Login user
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
            
            # Test API
            item_data = {
                'item_type': 'book',
                'title': 'New Test Book',
                'authors': 'New Author',
                'language': 'English',
                'donor_id': donor.id,
                'date_of_donation': '2024-01-01',
                'total_quantity': 5
            }
            
            response = client.post('/api/inventory',
                                 data=json.dumps(item_data),
                                 content_type='application/json')
            
            assert response.status_code == 201
            
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['data']['item']['title'] == 'New Test Book'
    
    def test_create_inventory_item_forbidden(self, app, client):
        """Test creating inventory item as Student (forbidden)"""
        with app.app_context():
            # Create student user
            user = User.create_user(
                name="Test Student",
                roll_number="STU002",
                branch="CSE",
                batch="2021-2025",
                phone="9876543210",
                email="student2@test.com",
                password="password123"
            )
            user.status = UserStatus.ACTIVE
            
            role = Role.get_by_name('Student')
            user.roles.append(role)
            
            # Create donor
            donor = Donor(
                name="Test Donor",
                branch="CSE",
                batch="2020-2024"
            )
            
            db.session.add_all([user, donor])
            db.session.commit()
            
            # Login user
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
            
            # Test API
            item_data = {
                'item_type': 'book',
                'title': 'New Test Book',
                'donor_id': donor.id,
                'date_of_donation': '2024-01-01',
                'total_quantity': 5
            }
            
            response = client.post('/api/inventory',
                                 data=json.dumps(item_data),
                                 content_type='application/json')
            
            assert response.status_code == 403
    
    def test_create_donor_success(self, app, client):
        """Test creating donor as Admin"""
        with app.app_context():
            # Create admin user
            user = User.create_user(
                name="Test Admin",
                roll_number="ADMIN002",
                branch="CSE",
                batch="2021-2025",
                phone="9876543210",
                email="admin2@test.com",
                password="password123"
            )
            user.status = UserStatus.ACTIVE
            
            role = Role.get_by_name('Admin')
            user.roles.append(role)
            
            db.session.add(user)
            db.session.commit()
            
            # Login user
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
            
            # Test API
            donor_data = {
                'name': 'New Donor',
                'branch': 'CSE',
                'batch': '2020-2024',
                'email': 'newdonor@test.com',
                'phone': '9876543210'
            }
            
            response = client.post('/api/donors',
                                 data=json.dumps(donor_data),
                                 content_type='application/json')
            
            assert response.status_code == 201
            
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['data']['donor']['name'] == 'New Donor'
    
    def test_search_suggestions_success(self, app, client):
        """Test search suggestions endpoint"""
        with app.app_context():
            # Create user
            user = User.create_user(
                name="Test Student",
                roll_number="STU003",
                branch="CSE",
                batch="2021-2025",
                phone="9876543210",
                email="student3@test.com",
                password="password123"
            )
            user.status = UserStatus.ACTIVE
            
            role = Role.get_by_name('Student')
            user.roles.append(role)
            
            # Create test data
            donor = Donor(name="Test Donor", branch="CSE", batch="2020-2024")
            
            db.session.add_all([user, donor])
            db.session.commit()
            
            item = InventoryItem(
                item_type=ItemType.BOOK,
                title="Python Programming Guide",
                authors="John Doe",
                donor_id=donor.id,
                total_quantity=5,
                available_quantity=3,
                date_of_donation=date.today()
            )
            db.session.add(item)
            db.session.commit()
            
            # Login user
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
            
            # Test API
            response = client.get('/api/search?q=Python')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'suggestions' in data['data']
    
    def test_inventory_analytics_success(self, app, client):
        """Test inventory analytics endpoint"""
        with app.app_context():
            # Create volunteer user
            user = User.create_user(
                name="Test Volunteer",
                roll_number="VOL001",
                branch="CSE",
                batch="2021-2025",
                phone="9876543210",
                email="volunteer@test.com",
                password="password123"
            )
            user.status = UserStatus.ACTIVE
            
            role = Role.get_by_name('Volunteer')
            user.roles.append(role)
            
            # Create test data
            donor = Donor(name="Analytics Donor", branch="CSE", batch="2020-2024")
            
            db.session.add_all([user, donor])
            db.session.commit()
            
            items = [
                InventoryItem(
                    item_type=ItemType.BOOK,
                    title="Available Book",
                    donor_id=donor.id,
                    total_quantity=10,
                    available_quantity=8,
                    date_of_donation=date.today()
                ),
                InventoryItem(
                    item_type=ItemType.LAPTOP,
                    title="Unavailable Laptop",
                    donor_id=donor.id,
                    total_quantity=5,
                    available_quantity=0,
                    date_of_donation=date.today()
                )
            ]
            db.session.add_all(items)
            db.session.commit()
            
            # Login user
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
            
            # Test API
            response = client.get('/api/inventory/analytics')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['success'] is True
            
            summary = data['data']['summary']
            assert 'total_items' in summary
            assert 'available_items' in summary
            assert 'unavailable_items' in summary
            assert 'availability_rate' in summary
    
    def test_inventory_analytics_forbidden(self, app, client):
        """Test analytics endpoint forbidden for students"""
        with app.app_context():
            # Create student user
            user = User.create_user(
                name="Test Student",
                roll_number="STU004",
                branch="CSE",
                batch="2021-2025",
                phone="9876543210",
                email="student4@test.com",
                password="password123"
            )
            user.status = UserStatus.ACTIVE
            
            role = Role.get_by_name('Student')
            user.roles.append(role)
            
            db.session.add(user)
            db.session.commit()
            
            # Login user
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
            
            # Test API
            response = client.get('/api/inventory/analytics')
            assert response.status_code == 403
            
            data = json.loads(response.data)
            assert data['success'] is False