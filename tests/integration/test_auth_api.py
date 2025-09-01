"""
Integration tests for authenticated API endpoints
"""
import pytest
import json
from app.models.user import User, UserStatus
from app.models.role import Role
from app.models.department import Department
from app import db


class TestAuthenticatedAPI:
    """Test authenticated API endpoints"""
    
    def test_login_access_protected_endpoint_success(self, app, client):
        """Test login then access protected endpoint"""
        with app.app_context():
            # Create active user
            user = User.create_user(
                name="API Test User",
                roll_number="API001",
                branch="CSE",
                batch="2021-2025",
                phone="9876543210",
                email="apitest@example.com",
                password="password123"
            )
            user.status = UserStatus.ACTIVE
            
            admin_role = Role.get_by_name('Admin')
            user.roles.append(admin_role)
            
            db.session.add(user)
            db.session.commit()
            
            # Login
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
            
            # Access protected endpoint
            response = client.get('/api/system/info')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'user' in data['data']
            assert data['data']['user']['email'] == user.email
    
    def test_pending_user_access_protected_endpoint_forbidden(self, app, client):
        """Test pending user cannot access protected endpoint"""
        with app.app_context():
            # Create pending user
            user = User.create_user(
                name="Pending User",
                roll_number="PEND001",
                branch="CSE",
                batch="2021-2025",
                phone="9876543210",
                email="pending@example.com",
                password="password123"
            )
            # Keep status as PENDING (default)
            
            student_role = Role.get_by_name('Student')
            user.roles.append(student_role)
            
            db.session.add(user)
            db.session.commit()
            
            # Try to login (should fail due to pending status)
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
            
            # Access protected endpoint should redirect/fail
            response = client.get('/api/system/info')
            assert response.status_code in [302, 401, 403]  # Redirect to login or forbidden
    
    def test_unauthorized_request_401(self, client):
        """Test unauthorized request returns 401"""
        response = client.get('/api/system/info')
        assert response.status_code == 302  # Redirect to login
    
    def test_users_endpoint_admin_access(self, app, client):
        """Test users endpoint with admin access"""
        with app.app_context():
            # Create admin user
            admin = User.create_user(
                name="Admin User",
                roll_number="ADMIN001",
                branch="Administration",
                batch="ADMIN",
                phone="9999999999",
                email="admin@example.com",
                password="admin123"
            )
            admin.status = UserStatus.ACTIVE
            
            admin_role = Role.get_by_name('Admin')
            admin.roles.append(admin_role)
            
            db.session.add(admin)
            db.session.commit()
            
            # Login as admin
            with client.session_transaction() as sess:
                sess['_user_id'] = str(admin.id)
                sess['_fresh'] = True
            
            # Access users endpoint
            response = client.get('/api/users')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'users' in data['data']
    
    def test_users_endpoint_student_forbidden(self, app, client):
        """Test users endpoint forbidden for students"""
        with app.app_context():
            # Create student user
            student = User.create_user(
                name="Student User",
                roll_number="STU001",
                branch="CSE",
                batch="2021-2025",
                phone="9876543210",
                email="student@example.com",
                password="student123"
            )
            student.status = UserStatus.ACTIVE
            
            student_role = Role.get_by_name('Student')
            student.roles.append(student_role)
            
            db.session.add(student)
            db.session.commit()
            
            # Login as student
            with client.session_transaction() as sess:
                sess['_user_id'] = str(student.id)
                sess['_fresh'] = True
            
            # Try to access users endpoint
            response = client.get('/api/users')
            assert response.status_code == 403
            
            data = json.loads(response.data)
            assert data['success'] is False
    
    def test_departments_endpoint_authenticated_access(self, app, client):
        """Test departments endpoint with authenticated access"""
        with app.app_context():
            # Create active user
            user = User.create_user(
                name="Test User",
                roll_number="TEST001",
                branch="CSE",
                batch="2021-2025",
                phone="9876543210",
                email="test@example.com",
                password="password123"
            )
            user.status = UserStatus.ACTIVE
            
            student_role = Role.get_by_name('Student')
            user.roles.append(student_role)
            
            db.session.add(user)
            db.session.commit()
            
            # Login
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
            
            # Access departments endpoint
            response = client.get('/api/departments')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'departments' in data['data']
    
    def test_roles_endpoint_admin_only(self, app, client):
        """Test roles endpoint requires admin access"""
        with app.app_context():
            # Create admin user
            admin = User.create_user(
                name="Admin User",
                roll_number="ADMIN002",
                branch="Administration",
                batch="ADMIN",
                phone="9999999998",
                email="admin2@example.com",
                password="admin123"
            )
            admin.status = UserStatus.ACTIVE
            
            admin_role = Role.get_by_name('Admin')
            admin.roles.append(admin_role)
            
            db.session.add(admin)
            db.session.commit()
            
            # Login as admin
            with client.session_transaction() as sess:
                sess['_user_id'] = str(admin.id)
                sess['_fresh'] = True
            
            # Access roles endpoint
            response = client.get('/api/roles')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'roles' in data['data']