"""
Integration tests for validation error handling and improved error messages
"""
import pytest
import json
from app.models.user import User, UserStatus
from app.models.role import Role
from app.models.donor import Donor
from app.models.inventory_item import InventoryItem, ItemType
from app import db


class TestValidationErrorHandling:
    """Test improved validation error messages"""
    
    def create_test_user(self, app, role_name='Admin'):
        """Helper to create test user"""
        with app.app_context():
            user = User.create_user(
                name=f"Validation Test {role_name}",
                roll_number=f"VAL{role_name.upper()}001",
                branch="CSE",
                batch="2021-2025",
                phone="9876543210",
                email=f"validation{role_name.lower()}@test.com",
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
    
    def test_donor_validation_missing_required_fields(self, app, client):
        """Test donor validation with missing required fields"""
        user = self.create_test_user(app, 'Admin')
        self.login_user(client, user)
        
        # Test missing name
        invalid_data = {
            'branch': 'CSE',
            'batch': '2020-2024'
            # Missing name
        }
        
        response = client.post('/api/donors',
                             data=json.dumps(invalid_data),
                             content_type='application/json')
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'name' in data['message'].lower() or 'name' in str(data['error']['details'])
        assert 'required' in data['message'].lower() or 'required' in str(data['error']['details'])
    
    def test_donor_validation_invalid_email(self, app, client):
        """Test donor validation with invalid email format"""
        user = self.create_test_user(app, 'Admin')
        self.login_user(client, user)
        
        invalid_data = {
            'name': 'Test Donor',
            'branch': 'CSE',
            'batch': '2020-2024',
            'email': 'not-a-valid-email'
        }
        
        response = client.post('/api/donors',
                             data=json.dumps(invalid_data),
                             content_type='application/json')
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'email' in data['message'].lower()
        assert 'format' in data['message'].lower() or 'invalid' in data['message'].lower()
    
    def test_donor_validation_field_length_limits(self, app, client):
        """Test donor validation with field length violations"""
        user = self.create_test_user(app, 'Admin')
        self.login_user(client, user)
        
        # Test name too long
        invalid_data = {
            'name': 'A' * 101,  # Exceeds 100 character limit
            'branch': 'CSE',
            'batch': '2020-2024'
        }
        
        response = client.post('/api/donors',
                             data=json.dumps(invalid_data),
                             content_type='application/json')
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'name' in str(data['error']['details']).lower()
        assert 'characters' in data['message'].lower() or 'characters' in str(data['error']['details']).lower()
    
    def test_inventory_validation_missing_required_fields(self, app, client):
        """Test inventory item validation with missing required fields"""
        user = self.create_test_user(app, 'Admin')
        self.login_user(client, user)
        
        # Test missing title
        invalid_data = {
            'item_type': 'book',
            'donor_id': 1,
            'date_of_donation': '2024-01-01',
            'total_quantity': 5
            # Missing title
        }
        
        response = client.post('/api/inventory',
                             data=json.dumps(invalid_data),
                             content_type='application/json')
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'title' in data['message'].lower() or 'title' in str(data['error']['details'])
    
    def test_inventory_validation_invalid_item_type(self, app, client):
        """Test inventory item validation with invalid item type"""
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
        assert 'item_type' in str(data['error']['details']).lower()
        assert any(item_type in str(data['error']['details']).lower() 
                  for item_type in ['book', 'laptop', 'kit'])
    
    def test_inventory_validation_invalid_donor_id(self, app, client):
        """Test inventory item validation with non-existent donor"""
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
        assert 'donor' in data['message'].lower()
        assert 'exist' in data['message'].lower() or 'not found' in data['message'].lower()
    
    def test_inventory_validation_negative_quantity(self, app, client):
        """Test inventory item validation with negative quantity"""
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
        assert 'quantity' in data['message'].lower()
        assert 'least 1' in data['message'].lower() or 'at least 1' in str(data['error']['details']).lower()
    
    def test_inventory_validation_invalid_date_format(self, app, client):
        """Test inventory item validation with invalid date format"""
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
            'date_of_donation': 'invalid-date-format',
            'total_quantity': 5
        }
        
        response = client.post('/api/inventory',
                             data=json.dumps(invalid_data),
                             content_type='application/json')
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'date' in data['message'].lower()
        assert 'format' in data['message'].lower() or 'yyyy-mm-dd' in str(data['error']['details']).lower()
    
    def test_validation_error_response_structure(self, app, client):
        """Test that validation error responses have consistent structure"""
        user = self.create_test_user(app, 'Admin')
        self.login_user(client, user)
        
        # Send invalid data to trigger validation error
        invalid_data = {
            'name': '',  # Empty name
            'branch': '',  # Empty branch
            'batch': ''  # Empty batch
        }
        
        response = client.post('/api/donors',
                             data=json.dumps(invalid_data),
                             content_type='application/json')
        
        assert response.status_code == 422
        data = json.loads(response.data)
        
        # Check response structure
        assert 'success' in data
        assert data['success'] is False
        assert 'message' in data
        assert 'timestamp' in data
        assert 'error' in data
        assert 'code' in data['error']
        assert 'details' in data['error']
        assert data['error']['code'] == 'VALIDATION_ERROR'
        
        # Check that details contain field-specific errors
        assert isinstance(data['error']['details'], dict)
        assert len(data['error']['details']) > 0
    
    def test_multiple_validation_errors(self, app, client):
        """Test handling of multiple validation errors"""
        user = self.create_test_user(app, 'Admin')
        self.login_user(client, user)
        
        # Data with multiple validation errors
        invalid_data = {
            'name': 'A' * 101,  # Too long
            'branch': '',  # Empty
            'batch': '',  # Empty
            'email': 'invalid-email',  # Invalid format
            'phone': 'A' * 20  # Too long
        }
        
        response = client.post('/api/donors',
                             data=json.dumps(invalid_data),
                             content_type='application/json')
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert data['success'] is False
        
        # Should have multiple field errors
        details = data['error']['details']
        assert len(details) > 1
        
        # Check that message mentions multiple fields
        if len(details) > 1:
            assert 'check the following fields' in data['message'].lower()
    
    def test_malformed_json_error(self, app, client):
        """Test handling of malformed JSON"""
        user = self.create_test_user(app, 'Admin')
        self.login_user(client, user)
        
        # Send malformed JSON
        response = client.post('/api/donors',
                             data='{"invalid": json, "missing": quote}',
                             content_type='application/json')
        
        # Should handle gracefully
        assert response.status_code in [400, 422]
        
        if response.status_code == 400:
            data = json.loads(response.data)
            assert data['success'] is False
    
    def test_content_type_validation(self, app, client):
        """Test validation of content type"""
        user = self.create_test_user(app, 'Admin')
        self.login_user(client, user)
        
        # Send data without proper content type
        response = client.post('/api/donors',
                             data='{"name": "Test", "branch": "CSE", "batch": "2020-2024"}')
        
        # Should handle gracefully
        assert response.status_code in [400, 422]
    
    def test_empty_request_body(self, app, client):
        """Test handling of empty request body"""
        user = self.create_test_user(app, 'Admin')
        self.login_user(client, user)
        
        # Send empty body
        response = client.post('/api/donors',
                             data='',
                             content_type='application/json')
        
        # Should handle gracefully
        assert response.status_code in [400, 422]
        
        if response.status_code == 422:
            data = json.loads(response.data)
            assert data['success'] is False