"""
Unit tests for database models
"""
import pytest
from app.models.user import User, UserStatus
from app.models.role import Role
from app.models.department import Department
from app.models.audit_log import AuditLog, AuditAction, AuditSeverity
from app import db


class TestUserModel:
    """Test User model"""
    
    def test_create_user(self, app):
        """Test user creation"""
        with app.app_context():
            user = User.create_user(
                name="Test User",
                roll_number="TEST001",
                branch="CSE",
                batch="2021-2025",
                phone="9876543210",
                email="test@example.com",
                password="password123"
            )
            
            assert user.name == "Test User"
            assert user.roll_number == "TEST001"
            assert user.email == "test@example.com"
            assert user.status == UserStatus.PENDING
            assert user.check_password("password123")
    
    def test_password_hashing(self, app):
        """Test password hashing and verification"""
        with app.app_context():
            user = User.create_user(
                name="Test User",
                roll_number="TEST001",
                branch="CSE",
                batch="2021-2025",
                phone="9876543210",
                email="test@example.com",
                password="password123"
            )
            
            assert user.password_hash != "password123"
            assert user.check_password("password123")
            assert not user.check_password("wrongpassword")
    
    def test_user_roles(self, app):
        """Test user role assignment"""
        with app.app_context():
            user = User.create_user(
                name="Test User",
                roll_number="TEST001",
                branch="CSE",
                batch="2021-2025",
                phone="9876543210",
                email="test@example.com",
                password="password123"
            )
            
            student_role = Role.get_by_name('Student')
            user.roles.append(student_role)
            
            assert user.has_role('Student')
            assert not user.has_role('Admin')
            assert 'Student' in user.get_role_names()
    
    def test_user_permissions(self, app):
        """Test user permissions"""
        with app.app_context():
            user = User.create_user(
                name="Test User",
                roll_number="TEST001",
                branch="CSE",
                batch="2021-2025",
                phone="9876543210",
                email="test@example.com",
                password="password123"
            )
            
            admin_role = Role.get_by_name('Admin')
            user.roles.append(admin_role)
            
            permissions = user.get_permissions()
            assert 'manage_users' in permissions
            assert 'manage_inventory' in permissions


class TestRoleModel:
    """Test Role model"""
    
    def test_default_roles_creation(self, app):
        """Test default roles are created"""
        with app.app_context():
            roles = Role.get_all_roles()
            role_names = [role.name for role in roles]
            
            assert 'Admin' in role_names
            assert 'Incharge' in role_names
            assert 'Volunteer' in role_names
            assert 'Student' in role_names
    
    def test_role_permissions(self, app):
        """Test role permissions"""
        with app.app_context():
            admin_role = Role.get_by_name('Admin')
            student_role = Role.get_by_name('Student')
            
            admin_permissions = admin_role.get_permissions()
            student_permissions = student_role.get_permissions()
            
            assert 'manage_users' in admin_permissions
            assert 'manage_users' not in student_permissions
            assert 'request_checkout' in student_permissions
    
    def test_role_hierarchy(self, app):
        """Test role hierarchy"""
        with app.app_context():
            admin_role = Role.get_by_name('Admin')
            student_role = Role.get_by_name('Student')
            
            assert admin_role.can_manage_role(student_role)
            assert not student_role.can_manage_role(admin_role)


class TestDepartmentModel:
    """Test Department model"""
    
    def test_default_departments_creation(self, app):
        """Test default departments are created"""
        with app.app_context():
            departments = Department.get_active_departments()
            dept_codes = [dept.code for dept in departments]
            
            assert 'CSE' in dept_codes
            assert 'ECE' in dept_codes
            assert 'EEE' in dept_codes
    
    def test_department_branch_mapping(self, app):
        """Test department branch mapping"""
        with app.app_context():
            cse_dept = Department.get_department_by_branch('CSE')
            assert cse_dept is not None
            assert cse_dept.code == 'CSE'
            
            cs_dept = Department.get_department_by_branch('Computer Science')
            assert cs_dept is not None
            assert cs_dept.code == 'CSE'


class TestAuditLogModel:
    """Test AuditLog model"""
    
    def test_audit_log_creation(self, app):
        """Test audit log creation"""
        with app.app_context():
            audit_log = AuditLog.log_action(
                action=AuditAction.LOGIN,
                description="Test login action",
                severity=AuditSeverity.INFO
            )
            
            assert audit_log.action == AuditAction.LOGIN
            assert audit_log.description == "Test login action"
            assert audit_log.severity == AuditSeverity.INFO
    
    def test_audit_log_with_user(self, app):
        """Test audit log with user context"""
        with app.app_context():
            # Create user within the same app context
            student = User.create_user(
                name="Test Student",
                roll_number="CS002",
                branch="CSE",
                batch="2021-2025",
                phone="9876543210",
                email="student2@test.com",
                password="student123"
            )
            student.status = UserStatus.ACTIVE
            
            student_role = Role.get_by_name('Student')
            student.roles.append(student_role)
            
            db.session.add(student)
            db.session.commit()
            
            # Create audit log with fresh user data
            audit_log = AuditLog(
                action=AuditAction.USER_UPDATE,
                description=f"User {student.email} updated profile",
                user_id=student.id,
                user_email=student.email,
                user_name=student.name,
                target_type='User',
                target_id=student.id,
                severity=AuditSeverity.INFO
            )
            
            db.session.add(audit_log)
            db.session.commit()
            
            assert audit_log.user_id == student.id
            assert audit_log.user_email == student.email
            assert audit_log.target_type == 'User'