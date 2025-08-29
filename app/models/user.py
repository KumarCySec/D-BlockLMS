"""
User model for authentication and profile management
"""
from datetime import datetime
from enum import Enum
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class UserStatus(Enum):
    """User account status enumeration"""
    PENDING = 'pending'
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    SUSPENDED = 'suspended'


# Association table for many-to-many relationship between users and roles
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True)
)


class User(UserMixin, db.Model):
    """User model with authentication and profile information"""
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Required fields as per requirements
    name = db.Column(db.String(100), nullable=False)
    roll_number = db.Column(db.String(20), nullable=False, unique=True)
    branch = db.Column(db.String(50), nullable=False)
    batch = db.Column(db.String(10), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    
    # Authentication fields
    password_hash = db.Column(db.String(128), nullable=False)
    status = db.Column(db.Enum(UserStatus), default=UserStatus.PENDING, nullable=False)
    
    # Department relationship
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    roles = db.relationship('Role', secondary=user_roles, backref=db.backref('users', lazy='dynamic'))
    department = db.relationship('Department', backref='users')
    
    # Indexes
    __table_args__ = (
        db.Index('idx_user_email', 'email'),
        db.Index('idx_user_roll_number', 'roll_number'),
        db.Index('idx_user_status', 'status'),
        db.Index('idx_user_department', 'department_id'),
    )
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    def set_password(self, password):
        """Set password hash using bcrypt"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def has_role(self, role_name):
        """Check if user has a specific role"""
        return any(role.name == role_name for role in self.roles)
    
    def get_role_names(self):
        """Get list of role names for the user"""
        return [role.name for role in self.roles]
    
    def is_active_user(self):
        """Check if user account is active"""
        return self.status == UserStatus.ACTIVE
    
    def is_pending_approval(self):
        """Check if user is pending approval"""
        return self.status == UserStatus.PENDING
    
    def can_approve_users(self):
        """Check if user can approve other users"""
        return self.has_role('Admin') or self.has_role('Incharge')
    
    def can_manage_inventory(self):
        """Check if user can manage inventory"""
        return self.has_role('Admin') or self.has_role('Incharge')
    
    def can_approve_transactions(self):
        """Check if user can approve transactions"""
        return self.has_role('Admin') or self.has_role('Incharge') or self.has_role('Volunteer')
    
    def get_permissions(self):
        """Get all permissions for the user"""
        permissions = set()
        for role in self.roles:
            permissions.update(role.get_permissions())
        return list(permissions)
    
    def to_dict(self, include_sensitive=False):
        """Convert user to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'roll_number': self.roll_number,
            'branch': self.branch,
            'batch': self.batch,
            'email': self.email,
            'status': self.status.value,
            'department_id': self.department_id,
            'department_name': self.department.name if self.department else None,
            'roles': [role.name for role in self.roles],
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
        
        if include_sensitive:
            data['phone'] = self.phone
            
        return data
    
    @classmethod
    def create_user(cls, name, roll_number, branch, batch, phone, email, password, department_id=None):
        """Create a new user with pending status"""
        user = cls(
            name=name,
            roll_number=roll_number,
            branch=branch,
            batch=batch,
            phone=phone,
            email=email,
            department_id=department_id,
            status=UserStatus.PENDING
        )
        user.set_password(password)
        return user
    
    @classmethod
    def get_by_email(cls, email):
        """Get user by email"""
        return cls.query.filter_by(email=email).first()
    
    @classmethod
    def get_by_roll_number(cls, roll_number):
        """Get user by roll number"""
        return cls.query.filter_by(roll_number=roll_number).first()
    
    @classmethod
    def get_pending_users(cls, department_id=None):
        """Get users pending approval"""
        query = cls.query.filter_by(status=UserStatus.PENDING)
        if department_id:
            query = query.filter_by(department_id=department_id)
        return query.all()
    
    @classmethod
    def get_active_users(cls, department_id=None):
        """Get active users"""
        query = cls.query.filter_by(status=UserStatus.ACTIVE)
        if department_id:
            query = query.filter_by(department_id=department_id)
        return query.all()