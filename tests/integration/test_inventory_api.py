"""
Integration tests for inventory API endpoints
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


class TestInventoryAPI:
    """Test inventory API endpoints"""
    
    def setup_method(self):
        """Set up test data for each test"""
        pass
    
    def create_test_user(self, app, role_name='Admin'):
        """Helper to create test user with specified role"""
        with app.app_context():
            user = User.create_user(
                name=f"Test {role_name}",
                roll_number=f"{role_name.upper()}001",
                branch="CSE",
                batch="2021-2025",
                phone="9876543210",
                email=f"{role_name.lower()}@test.com",
                password="password123"
            )
            user.status = UserStatus.ACTIVE
            
            role = Role.get_by_name(role_name)
            user.roles.append(role)
            
            db.session.add(user)
            db.session.commit()
            
            # Return the user ID instead of the object to avoid detached instance issues
            return user.id
    
    def create_test_donor(self, app):
        """Helper to create test donor"""
        with app.app_context():
            donor = Donor(
                name="Test Donor",
                branch="CSE",
                batch="2020-2024",
                email="donor@test.com",
                phone="9876543210"
            )
            db.session.add(donor)
            db.session.commit()
            return donor.id
    
    def create_test_inventory_item(self, app, donor_id):
        """Helper to create test inventory item"""
        with app.app_context():
            item = InventoryItem(
                item_type=ItemType.BOOK,
                title="Test Book",
                authors="Test Author",
                language="English",
                donor_id=donor_id,
                total_quantity=10,
                available_quantity=8,
                date_of_donation=date.today()
            )
            db.session.add(item)
            db.session.commit()
            return item.id
    
    def login_user(self, client, user_id):
        """Helper to login user"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user_id)
            sess['_fresh'] = True
    
    def test_get_inventory_unauthorized(self, client):
        """Test inventory endpoint without authentication"""
        response = client.get('/api/inventory')
        assert response.status_code == 302  # Redirect to login
    
    def test_get_inventory_success(self, app, client):
        """Test successful inventory retrieval"""
        user = self.create_test_user(app, 'Student')
        donor_id = self.create_test_donor(app)
        item = self.create_test_inventory_item(app, donor_id)
        
        self.login_user(client, user)
        
        response = client.get('/api/inventory')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'items' in data['data']
        assert 'pagination' in data['data']
        assert 'filters' in data['data']
        
        # Check item data
        items = data['data']['items']
        assert len(items) >= 1
        
        item_data = items[0]
        assert item_data['title'] == 'Test Book'
        assert item_data['item_type'] == 'book'
        assert item_data['donor']['name'] == 'Test Donor'
    
    def test_get_inventory_with_search(self, app, client):
        """Test inventory search functionality"""
        user = self.create_test_user(app, 'Student')
        donor_id = self.create_test_donor(app)
        
        with app.app_context():
            # Create multiple items
            items = [
                InventoryItem(
                    item_type=ItemType.BOOK,
                    title="Python Programming",
                    authors="John Doe",
                    donor_id=donor_id,
                    total_quantity=5,
                    available_quantity=3,
                    date_of_donation=date.today()
                ),
                InventoryItem(
                    item_type=ItemType.LAPTOP,
                    title="Dell Laptop",
                    authors="Dell Inc",
                    donor_id=donor_id,
                    total_quantity=2,
                    available_quantity=1,
                    date_of_donation=date.today()
                )
            ]
            db.session.add_all(items)
            db.session.commit()
        
        self.login_user(client, user)
        
        # Test search query
        response = client.get('/api/inventory?q=Python')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        items = data['data']['items']
        assert len(items) == 1
        assert items[0]['title'] == 'Python Programming'
    
    def test_get_inventory_with_filters(self, app, client):
        """Test inventory filtering"""
        user = self.create_test_user(app, 'Student')
        donor_id = self.create_test_donor(app)
        
        with app.app_context():
            # Create items of different types
            book = InventoryItem(
                item_type=ItemType.BOOK,
                title="Test Book",
                donor_id=donor_id,
                total_quantity=5,
                available_quantity=3,
                date_of_donation=date.today()
            )
            laptop = InventoryItem(
                item_type=ItemType.LAPTOP,
                title="Test Laptop",
                donor_id=donor_id,
                total_quantity=2,
                available_quantity=0,
                date_of_donation=date.today()
            )
            db.session.add_all([book, laptop])
            db.session.commit()
        
        self.login_user(client, user)
        
        # Test type filter
        response = client.get('/api/inventory?type=book')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        items = data['data']['items']
        assert len(items) == 1
        assert items[0]['item_type'] == 'book'
        
        # Test availability filter
        response = client.get('/api/inventory?availability=available')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        items = data['data']['items']
        assert len(items) == 1
        assert items[0]['available_quantity'] > 0
    
    def test_get_inventory_item_success(self, app, client):
        """Test getting specific inventory item"""
        user = self.create_test_user(app, 'Student')
        donor_id = self.create_test_donor(app)
        item = self.create_test_inventory_item(app, donor_id)
        
        self.login_user(client, user)
        
        response = client.get(f'/api/inventory/{item}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        
        item_data = data['data']['item']
        assert item_data['title'] == 'Test Book'
        assert item_data['donor']['name'] == 'Test Donor'
        assert 'transaction_history' in item_data
        assert 'current_borrowers' in item_data
        assert 'waitlist' in item_data
    
    def test_get_inventory_item_not_found(self, app, client):
        """Test getting non-existent inventory item"""
        user = self.create_test_user(app, 'Student')
        self.login_user(client, user)
        
        response = client.get('/api/inventory/99999')
        assert response.status_code == 404
    
    def test_create_inventory_item_success(self, app, client):
        """Test creating inventory item as Admin"""
        user = self.create_test_user(app, 'Admin')
        donor_id = self.create_test_donor(app)
        
        self.login_user(client, user)
        
        item_data = {
            'item_type': 'book',
            'title': 'New Test Book',
            'authors': 'New Author',
            'language': 'English',
            'donor_id': donor_id,
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
        assert data['data']['item']['available_quantity'] == 5  # Should equal total_quantity
    
    def test_create_inventory_item_validation_error(self, app, client):
        """Test creating inventory item with invalid data"""
        user = self.create_test_user(app, 'Admin')
        self.login_user(client, user)
        
        # Missing required fields
        item_data = {
            'item_type': 'book',
            # Missing title and donor_id
        }
        
        response = client.post('/api/inventory',
                             data=json.dumps(item_data),
                             content_type='application/json')
        
        assert response.status_code == 422
        
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'error' in data
    
    def test_create_inventory_item_forbidden(self, app, client):
        """Test creating inventory item as Student (forbidden)"""
        user = self.create_test_user(app, 'Student')
        donor_id = self.create_test_donor(app)
        
        self.login_user(client, user)
        
        item_data = {
            'item_type': 'book',
            'title': 'New Test Book',
            'donor_id': donor_id,
            'date_of_donation': '2024-01-01',
            'total_quantity': 5
        }
        
        response = client.post('/api/inventory',
                             data=json.dumps(item_data),
                             content_type='application/json')
        
        assert response.status_code == 403
    
    def test_update_inventory_item_success(self, app, client):
        """Test updating inventory item"""
        user = self.create_test_user(app, 'Admin')
        donor_id = self.create_test_donor(app)
        item = self.create_test_inventory_item(app, donor_id)
        
        self.login_user(client, user)
        
        update_data = {
            'item_type': 'book',
            'title': 'Updated Test Book',
            'authors': 'Updated Author',
            'language': 'English',
            'donor_id': donor_id,
            'date_of_donation': '2024-01-01',
            'total_quantity': 12  # Increase quantity
        }
        
        response = client.put(f'/api/inventory/{item}',
                            data=json.dumps(update_data),
                            content_type='application/json')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['item']['title'] == 'Updated Test Book'
        assert data['data']['item']['total_quantity'] == 12
    
    def test_update_inventory_item_quantity_validation(self, app, client):
        """Test updating inventory item with invalid quantity"""
        user = self.create_test_user(app, 'Admin')
        donor_id = self.create_test_donor(app)
        
        with app.app_context():
            # Create item with some borrowed items
            item = InventoryItem(
                item_type=ItemType.BOOK,
                title="Test Book",
                donor_id=donor_id,
                total_quantity=10,
                available_quantity=5,  # 5 are borrowed
                date_of_donation=date.today()
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id
        
        self.login_user(client, user)
        
        # Try to reduce total quantity below borrowed count
        update_data = {
            'item_type': 'book',
            'title': 'Test Book',
            'donor_id': donor_id,
            'date_of_donation': '2024-01-01',
            'total_quantity': 3  # Less than borrowed count (5)
        }
        
        response = client.put(f'/api/inventory/{item_id}',
                            data=json.dumps(update_data),
                            content_type='application/json')
        
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'borrowed count' in data['message']
    
    def test_delete_inventory_item_success(self, app, client):
        """Test deleting inventory item as Admin"""
        user = self.create_test_user(app, 'Admin')
        donor_id = self.create_test_donor(app)
        item = self.create_test_inventory_item(app, donor_id)
        
        self.login_user(client, user)
        
        response = client.delete(f'/api/inventory/{item}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'deleted successfully' in data['message']
    
    def test_delete_inventory_item_with_active_transactions(self, app, client):
        """Test deleting inventory item with active transactions"""
        user = self.create_test_user(app, 'Admin')
        donor_id = self.create_test_donor(app)
        
        with app.app_context():
            # Create item with borrowed items (simulated by available < total)
            item = InventoryItem(
                item_type=ItemType.BOOK,
                title="Borrowed Book",
                donor_id=donor_id,
                total_quantity=10,
                available_quantity=5,  # 5 are borrowed
                date_of_donation=date.today()
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id
        
        self.login_user(client, user)
        
        response = client.delete(f'/api/inventory/{item_id}')
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'active transactions' in data['message']


class TestDonorAPI:
    """Test donor API endpoints"""
    
    def create_test_user(self, app, role_name='Admin'):
        """Helper to create test user with specified role"""
        with app.app_context():
            user = User.create_user(
                name=f"Test {role_name}",
                roll_number=f"{role_name.upper()}002",
                branch="CSE",
                batch="2021-2025",
                phone="9876543210",
                email=f"{role_name.lower()}2@test.com",
                password="password123"
            )
            user.status = UserStatus.ACTIVE
            
            role = Role.get_by_name(role_name)
            user.roles.append(role)
            
            db.session.add(user)
            db.session.commit()
            
            return user.id
    
    def login_user(self, client, user_id):
        """Helper to login user"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user_id)
            sess['_fresh'] = True
    
    def test_get_donors_success(self, app, client):
        """Test successful donor retrieval"""
        user = self.create_test_user(app, 'Student')
        
        with app.app_context():
            # Create test donors
            donors = [
                Donor(name="Alice Johnson", branch="CSE", batch="2020-2024"),
                Donor(name="Bob Smith", branch="ECE", batch="2019-2023")
            ]
            db.session.add_all(donors)
            db.session.commit()
        
        self.login_user(client, user)
        
        response = client.get('/api/donors')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'donors' in data['data']
        assert 'pagination' in data['data']
        assert 'filters' in data['data']
        
        donors_data = data['data']['donors']
        assert len(donors_data) >= 2
    
    def test_get_donors_with_search(self, app, client):
        """Test donor search functionality"""
        user = self.create_test_user(app, 'Student')
        
        with app.app_context():
            donors = [
                Donor(name="Alice Johnson", branch="CSE", batch="2020-2024"),
                Donor(name="Bob Smith", branch="ECE", batch="2019-2023")
            ]
            db.session.add_all(donors)
            db.session.commit()
        
        self.login_user(client, user)
        
        response = client.get('/api/donors?q=Alice')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        donors_data = data['data']['donors']
        assert len(donors_data) == 1
        assert donors_data[0]['name'] == 'Alice Johnson'
    
    def test_get_donor_detail(self, app, client):
        """Test getting specific donor details"""
        user = self.create_test_user(app, 'Student')
        
        with app.app_context():
            donor = Donor(
                name="Test Donor",
                branch="CSE",
                batch="2020-2024",
                email="donor@test.com"
            )
            db.session.add(donor)
            db.session.commit()
            donor_id = donor.id
        
        self.login_user(client, user)
        
        response = client.get(f'/api/donors/{donor_id}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        
        donor_data = data['data']['donor']
        assert donor_data['name'] == 'Test Donor'
        assert donor_data['email'] == 'donor@test.com'
        assert 'donations' in donor_data
    
    def test_create_donor_success(self, app, client):
        """Test creating donor as Admin"""
        user = self.create_test_user(app, 'Admin')
        self.login_user(client, user)
        
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
    
    def test_create_donor_validation_error(self, app, client):
        """Test creating donor with invalid data"""
        user = self.create_test_user(app, 'Admin')
        self.login_user(client, user)
        
        # Missing required fields
        donor_data = {
            'name': 'Test Donor',
            # Missing branch and batch
        }
        
        response = client.post('/api/donors',
                             data=json.dumps(donor_data),
                             content_type='application/json')
        
        assert response.status_code == 422
        
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_create_donor_duplicate_email(self, app, client):
        """Test creating donor with duplicate email"""
        user = self.create_test_user(app, 'Admin')
        
        with app.app_context():
            # Create existing donor
            existing_donor = Donor(
                name="Existing Donor",
                branch="CSE",
                batch="2020-2024",
                email="duplicate@test.com"
            )
            db.session.add(existing_donor)
            db.session.commit()
        
        self.login_user(client, user)
        
        donor_data = {
            'name': 'New Donor',
            'branch': 'ECE',
            'batch': '2021-2025',
            'email': 'duplicate@test.com'  # Same email
        }
        
        response = client.post('/api/donors',
                             data=json.dumps(donor_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'already exists' in data['message']
    
    def test_update_donor_success(self, app, client):
        """Test updating donor"""
        user = self.create_test_user(app, 'Admin')
        
        with app.app_context():
            donor = Donor(
                name="Original Name",
                branch="CSE",
                batch="2020-2024"
            )
            db.session.add(donor)
            db.session.commit()
            donor_id = donor.id
        
        self.login_user(client, user)
        
        update_data = {
            'name': 'Updated Name',
            'branch': 'ECE',
            'batch': '2020-2024',
            'email': 'updated@test.com'
        }
        
        response = client.put(f'/api/donors/{donor_id}',
                            data=json.dumps(update_data),
                            content_type='application/json')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['donor']['name'] == 'Updated Name'
        assert data['data']['donor']['email'] == 'updated@test.com'
    
    def test_delete_donor_success(self, app, client):
        """Test deleting donor as Admin"""
        user = self.create_test_user(app, 'Admin')
        
        with app.app_context():
            donor = Donor(
                name="To Delete",
                branch="CSE",
                batch="2020-2024"
            )
            db.session.add(donor)
            db.session.commit()
            donor_id = donor.id
        
        self.login_user(client, user)
        
        response = client.delete(f'/api/donors/{donor_id}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'deleted successfully' in data['message']
    
    def test_delete_donor_with_inventory(self, app, client):
        """Test deleting donor with associated inventory items"""
        user = self.create_test_user(app, 'Admin')
        
        with app.app_context():
            donor = Donor(
                name="Donor with Items",
                branch="CSE",
                batch="2020-2024"
            )
            db.session.add(donor)
            db.session.commit()
            
            # Add inventory item
            item = InventoryItem(
                item_type=ItemType.BOOK,
                title="Donated Book",
                donor_id=donor.id,
                total_quantity=1,
                available_quantity=1,
                date_of_donation=date.today()
            )
            db.session.add(item)
            db.session.commit()
            
            donor_id = donor.id
        
        self.login_user(client, user)
        
        response = client.delete(f'/api/donors/{donor_id}')
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'associated inventory items' in data['message']


class TestSearchAPI:
    """Test search API endpoints"""
    
    def create_test_user(self, app, role_name='Student'):
        """Helper to create test user"""
        with app.app_context():
            user = User.create_user(
                name=f"Test {role_name}",
                roll_number=f"{role_name.upper()}003",
                branch="CSE",
                batch="2021-2025",
                phone="9876543210",
                email=f"{role_name.lower()}3@test.com",
                password="password123"
            )
            user.status = UserStatus.ACTIVE
            
            role = Role.get_by_name(role_name)
            user.roles.append(role)
            
            db.session.add(user)
            db.session.commit()
            
            return user.id
    
    def login_user(self, client, user_id):
        """Helper to login user"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user_id)
            sess['_fresh'] = True
    
    def test_search_suggestions_success(self, app, client):
        """Test search suggestions endpoint"""
        user = self.create_test_user(app)
        
        with app.app_context():
            # Create test data
            donor = Donor(name="Test Donor", branch="CSE", batch="2020-2024")
            db.session.add(donor)
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
        
        self.login_user(client, user)
        
        response = client.get('/api/search?q=Python')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'suggestions' in data['data']
        
        suggestions = data['data']['suggestions']
        assert 'items' in suggestions
        assert 'donors' in suggestions
    
    def test_search_suggestions_short_query(self, app, client):
        """Test search suggestions with short query"""
        user = self.create_test_user(app)
        self.login_user(client, user)
        
        response = client.get('/api/search?q=P')  # Too short
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'at least 2 characters' in data['message']
    
    def test_popular_searches(self, app, client):
        """Test popular searches endpoint"""
        user = self.create_test_user(app)
        self.login_user(client, user)
        
        response = client.get('/api/search/popular')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'popular_items' in data['data']
        assert 'recent_additions' in data['data']
        assert 'popular_filters' in data['data']


class TestAnalyticsAPI:
    """Test analytics API endpoints"""
    
    def create_test_user(self, app, role_name='Volunteer'):
        """Helper to create test user"""
        with app.app_context():
            user = User.create_user(
                name=f"Test {role_name}",
                roll_number=f"{role_name.upper()}004",
                branch="CSE",
                batch="2021-2025",
                phone="9876543210",
                email=f"{role_name.lower()}4@test.com",
                password="password123"
            )
            user.status = UserStatus.ACTIVE
            
            role = Role.get_by_name(role_name)
            user.roles.append(role)
            
            db.session.add(user)
            db.session.commit()
            
            return user.id
    
    def login_user(self, client, user_id):
        """Helper to login user"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user_id)
            sess['_fresh'] = True
    
    def test_inventory_analytics_success(self, app, client):
        """Test inventory analytics endpoint"""
        user = self.create_test_user(app, 'Volunteer')
        
        with app.app_context():
            # Create test data
            donor = Donor(name="Analytics Donor", branch="CSE", batch="2020-2024")
            db.session.add(donor)
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
        
        self.login_user(client, user)
        
        response = client.get('/api/inventory/analytics')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        
        summary = data['data']['summary']
        assert 'total_items' in summary
        assert 'available_items' in summary
        assert 'unavailable_items' in summary
        assert 'availability_rate' in summary
        
        assert summary['total_items'] >= 2
        assert summary['available_items'] >= 1
        assert summary['unavailable_items'] >= 1
        
        assert 'items_by_type' in data['data']
        assert 'popular_items' in data['data']
        assert 'recent_additions' in data['data']
    
    def test_inventory_analytics_forbidden(self, app, client):
        """Test analytics endpoint forbidden for students"""
        user = self.create_test_user(app, 'Student')
        self.login_user(client, user)
        
        response = client.get('/api/inventory/analytics')
        assert response.status_code == 403
        
        data = json.loads(response.data)
        assert data['success'] is False


class TestInventoryAPIErrorHandling:
    """Test error handling and edge cases for inventory API"""
    
    def create_test_user(self, app, role_name='Admin'):
        """Helper to create test user"""
        with app.app_context():
            user = User.create_user(
                name=f"Error Test {role_name}",
                roll_number=f"ERR{role_name.upper()}001",
                branch="CSE",
                batch="2021-2025",
                phone="9876543210",
                email=f"error{role_name.lower()}@test.com",
                password="password123"
            )
            user.status = UserStatus.ACTIVE
            
            role = Role.get_by_name(role_name)
            user.roles.append(role)
            
            db.session.add(user)
            db.session.commit()
            
            return user.id
    
    def login_user(self, client, user_id):
        """Helper to login user"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user_id)
            sess['_fresh'] = True
    
    def test_inventory_validation_errors(self, app, client):
        """Test comprehensive validation error handling"""
        user = self.create_test_user(app, 'Admin')
        self.login_user(client, user)
        
        # Test missing required fields
        invalid_data = {
            'item_type': 'book',
            # Missing title and donor_id
            'total_quantity': 5
        }
        
        response = client.post('/api/inventory',
                             data=json.dumps(invalid_data),
                             content_type='application/json')
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'error' in data
        assert 'title' in str(data['error']) or 'donor_id' in str(data['error'])
    
    def test_inventory_invalid_item_type(self, app, client):
        """Test invalid item type validation"""
        user = self.create_test_user(app, 'Admin')
        
        with app.app_context():
            donor = Donor(name="Test Donor", branch="CSE", batch="2020-2024")
            db.session.add(donor)
            db.session.commit()
            donor_id = donor.id
        
        self.login_user(client, user)
        
        invalid_data = {
            'item_type': 'invalid_type',
            'title': 'Test Item',
            'donor_id': donor_id,
            'date_of_donation': '2024-01-01',
            'total_quantity': 5
        }
        
        response = client.post('/api/inventory',
                             data=json.dumps(invalid_data),
                             content_type='application/json')
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_inventory_invalid_donor_id(self, app, client):
        """Test invalid donor ID validation"""
        user = self.create_test_user(app, 'Admin')
        self.login_user(client, user)
        
        invalid_data = {
            'item_type': 'book',
            'title': 'Test Item',
            'donor_id': 99999,  # Non-existent donor
            'date_of_donation': '2024-01-01',
            'total_quantity': 5
        }
        
        response = client.post('/api/inventory',
                             data=json.dumps(invalid_data),
                             content_type='application/json')
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'donor' in str(data['error']).lower()
    
    def test_inventory_negative_quantity(self, app, client):
        """Test negative quantity validation"""
        user = self.create_test_user(app, 'Admin')
        
        with app.app_context():
            donor = Donor(name="Test Donor", branch="CSE", batch="2020-2024")
            db.session.add(donor)
            db.session.commit()
            donor_id = donor.id
        
        self.login_user(client, user)
        
        invalid_data = {
            'item_type': 'book',
            'title': 'Test Item',
            'donor_id': donor_id,
            'date_of_donation': '2024-01-01',
            'total_quantity': -5  # Negative quantity
        }
        
        response = client.post('/api/inventory',
                             data=json.dumps(invalid_data),
                             content_type='application/json')
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_inventory_malformed_json(self, app, client):
        """Test malformed JSON handling"""
        user = self.create_test_user(app, 'Admin')
        self.login_user(client, user)
        
        response = client.post('/api/inventory',
                             data='{"invalid": json}',
                             content_type='application/json')
        
        assert response.status_code in [400, 422]
    
    def test_inventory_unauthorized_operations(self, app, client):
        """Test unauthorized operations"""
        # Test without login
        response = client.get('/api/inventory')
        assert response.status_code == 302  # Redirect to login
        
        # Test student trying to create inventory
        student_user = self.create_test_user(app, 'Student')
        
        with app.app_context():
            donor = Donor(name="Test Donor", branch="CSE", batch="2020-2024")
            db.session.add(donor)
            db.session.commit()
            donor_id = donor.id
        
        self.login_user(client, student_user)
        
        item_data = {
            'item_type': 'book',
            'title': 'Unauthorized Item',
            'donor_id': donor_id,
            'date_of_donation': '2024-01-01',
            'total_quantity': 5
        }
        
        response = client.post('/api/inventory',
                             data=json.dumps(item_data),
                             content_type='application/json')
        
        assert response.status_code == 403
    
    def test_donor_validation_errors(self, app, client):
        """Test donor validation error handling"""
        user = self.create_test_user(app, 'Admin')
        self.login_user(client, user)
        
        # Test missing required fields
        invalid_data = {
            'name': 'Test Donor',
            # Missing branch and batch
        }
        
        response = client.post('/api/donors',
                             data=json.dumps(invalid_data),
                             content_type='application/json')
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'error' in data
    
    def test_donor_invalid_email_format(self, app, client):
        """Test invalid email format validation"""
        user = self.create_test_user(app, 'Admin')
        self.login_user(client, user)
        
        invalid_data = {
            'name': 'Test Donor',
            'branch': 'CSE',
            'batch': '2020-2024',
            'email': 'invalid-email-format'
        }
        
        response = client.post('/api/donors',
                             data=json.dumps(invalid_data),
                             content_type='application/json')
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_search_edge_cases(self, app, client):
        """Test search API edge cases"""
        user = self.create_test_user(app, 'Student')
        self.login_user(client, user)
        
        # Test very short query
        response = client.get('/api/search?q=a')
        assert response.status_code == 400
        
        # Test empty query
        response = client.get('/api/search?q=')
        assert response.status_code == 400
        
        # Test query with only spaces
        response = client.get('/api/search?q=   ')
        assert response.status_code == 400
    
    def test_pagination_edge_cases(self, app, client):
        """Test pagination edge cases"""
        user = self.create_test_user(app, 'Student')
        self.login_user(client, user)
        
        # Test invalid page numbers
        response = client.get('/api/inventory?page=0')
        assert response.status_code == 200  # Should default to page 1
        
        response = client.get('/api/inventory?page=-1')
        assert response.status_code == 200  # Should default to page 1
        
        # Test very large per_page (should be capped)
        response = client.get('/api/inventory?per_page=1000')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['data']['pagination']['per_page'] <= 100
    
    def test_filter_validation(self, app, client):
        """Test filter parameter validation"""
        user = self.create_test_user(app, 'Student')
        self.login_user(client, user)
        
        # Test invalid item type filter
        response = client.get('/api/inventory?type=invalid_type')
        assert response.status_code == 200  # Should ignore invalid filter
        
        # Test invalid availability filter
        response = client.get('/api/inventory?availability=invalid')
        assert response.status_code == 200  # Should ignore invalid filter
        
        # Test non-numeric department filter
        response = client.get('/api/inventory?department=not_a_number')
        assert response.status_code in [200, 400]  # Depends on implementation


class TestInventoryAPIPerformance:
    """Test performance-related aspects of inventory API"""
    
    def create_test_user(self, app, role_name='Student'):
        """Helper to create test user"""
        with app.app_context():
            user = User.create_user(
                name=f"Perf Test {role_name}",
                roll_number=f"PERF{role_name.upper()}001",
                branch="CSE",
                batch="2021-2025",
                phone="9876543210",
                email=f"perf{role_name.lower()}@test.com",
                password="password123"
            )
            user.status = UserStatus.ACTIVE
            
            role = Role.get_by_name(role_name)
            user.roles.append(role)
            
            db.session.add(user)
            db.session.commit()
            
            return user.id
    
    def login_user(self, client, user_id):
        """Helper to login user"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user_id)
            sess['_fresh'] = True
    
    def test_large_dataset_search(self, app, client):
        """Test search performance with larger dataset"""
        user = self.create_test_user(app, 'Student')
        
        with app.app_context():
            # Create donor
            donor = Donor(name="Performance Donor", branch="CSE", batch="2020-2024")
            db.session.add(donor)
            db.session.commit()
            
            # Create multiple items for performance testing
            items = []
            for i in range(50):  # Create 50 items
                item = InventoryItem(
                    item_type=ItemType.BOOK,
                    title=f"Performance Test Book {i}",
                    authors=f"Author {i}",
                    donor_id=donor.id,
                    total_quantity=5,
                    available_quantity=3,
                    date_of_donation=date.today()
                )
                items.append(item)
            
            db.session.add_all(items)
            db.session.commit()
        
        self.login_user(client, user)
        
        # Test search performance
        response = client.get('/api/inventory?q=Performance')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['data']['items']) > 0
    
    def test_complex_filtering(self, app, client):
        """Test complex filtering scenarios"""
        user = self.create_test_user(app, 'Student')
        
        with app.app_context():
            # Create test data with various combinations
            donors = [
                Donor(name="Donor A", branch="CSE", batch="2020-2024"),
                Donor(name="Donor B", branch="ECE", batch="2019-2023"),
            ]
            db.session.add_all(donors)
            db.session.commit()
            
            # Create department
            dept = Department(name="Computer Science", code="CSE")
            db.session.add(dept)
            db.session.commit()
            
            # Create items with different combinations
            items = [
                InventoryItem(
                    item_type=ItemType.BOOK,
                    title="CSE Book Available",
                    donor_id=donors[0].id,
                    department_id=dept.id,
                    language="English",
                    total_quantity=5,
                    available_quantity=3,
                    date_of_donation=date.today()
                ),
                InventoryItem(
                    item_type=ItemType.LAPTOP,
                    title="ECE Laptop Unavailable",
                    donor_id=donors[1].id,
                    language="English",
                    total_quantity=2,
                    available_quantity=0,
                    date_of_donation=date.today()
                ),
            ]
            db.session.add_all(items)
            db.session.commit()
        
        self.login_user(client, user)
        
        # Test multiple filters
        response = client.get('/api/inventory?type=book&availability=available&language=English')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Should return only available books in English
        items = data['data']['items']
        for item in items:
            assert item['item_type'] == 'book'
            assert item['available_quantity'] > 0
            assert item['language'] == 'English'