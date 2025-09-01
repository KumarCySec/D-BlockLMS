"""
Test configuration and fixtures
"""
import pytest
import tempfile
import os
from app import create_app, db
from app.models.user import User, UserStatus
from app.models.role import Role
from app.models.department import Department


@pytest.fixture
def app():
    """Create application for testing"""
    # Create temporary database
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app('testing')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        
        # Create default roles and departments
        Role.create_default_roles()
        Department.create_default_departments()
        
        yield app
        
        db.drop_all()
    
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create test CLI runner"""
    return app.test_cli_runner()


@pytest.fixture
def admin_user(app):
    """Create admin user for testing"""
    with app.app_context():
        admin = User.create_user(
            name="Admin User",
            roll_number="ADMIN001",
            branch="Administration",
            batch="ADMIN",
            phone="9999999999",
            email="admin@test.com",
            password="admin123"
        )
        admin.status = UserStatus.ACTIVE
        
        admin_role = Role.get_by_name('Admin')
        admin.roles.append(admin_role)
        
        db.session.add(admin)
        db.session.commit()
        
        return admin


@pytest.fixture
def student_user(app):
    """Create student user for testing"""
    with app.app_context():
        student = User.create_user(
            name="Test Student",
            roll_number="CS001",
            branch="CSE",
            batch="2021-2025",
            phone="9876543210",
            email="student@test.com",
            password="student123"
        )
        student.status = UserStatus.ACTIVE
        
        student_role = Role.get_by_name('Student')
        student.roles.append(student_role)
        
        cse_dept = Department.get_by_code('CSE')
        student.department_id = cse_dept.id
        
        db.session.add(student)
        db.session.commit()
        
        return student