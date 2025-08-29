"""
Role model for role-based access control
"""
from datetime import datetime
from app import db


class Role(db.Model):
    """Role model with hierarchical permissions"""
    __tablename__ = 'role'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    level = db.Column(db.Integer, nullable=False, default=0)  # Higher number = higher privilege
    is_system = db.Column(db.Boolean, default=False)  # System roles can't be deleted
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        db.Index('idx_role_name', 'name'),
        db.Index('idx_role_level', 'level'),
    )
    
    def __repr__(self):
        return f'<Role {self.name}>'
    
    def get_permissions(self):
        """Get permissions for this role"""
        permissions = []
        
        if self.name == 'Admin':
            permissions = [
                'manage_users', 'manage_roles', 'manage_departments',
                'manage_inventory', 'manage_donors', 'approve_transactions',
                'manage_volunteers', 'view_analytics', 'manage_system',
                'view_audit_logs', 'manage_fines', 'export_data'
            ]
        elif self.name == 'Incharge':
            permissions = [
                'manage_department_users', 'manage_inventory', 'manage_donors',
                'approve_transactions', 'manage_volunteers', 'view_analytics',
                'view_department_audit_logs', 'manage_fines'
            ]
        elif self.name == 'Volunteer':
            permissions = [
                'approve_transactions', 'view_inventory', 'manage_library_status',
                'view_volunteer_analytics', 'track_attendance'
            ]
        elif self.name == 'Student':
            permissions = [
                'request_checkout', 'view_inventory', 'join_waitlist',
                'view_own_transactions', 'request_renewal'
            ]
        
        return permissions
    
    def can_manage_role(self, other_role):
        """Check if this role can manage another role"""
        return self.level > other_role.level
    
    def to_dict(self):
        """Convert role to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'level': self.level,
            'is_system': self.is_system,
            'permissions': self.get_permissions(),
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def get_by_name(cls, name):
        """Get role by name"""
        return cls.query.filter_by(name=name).first()
    
    @classmethod
    def get_all_roles(cls):
        """Get all roles ordered by level"""
        return cls.query.order_by(cls.level.desc()).all()
    
    @classmethod
    def create_default_roles(cls):
        """Create default system roles"""
        default_roles = [
            {
                'name': 'Admin',
                'description': 'System administrator with full access',
                'level': 100,
                'is_system': True
            },
            {
                'name': 'Incharge',
                'description': 'Department incharge with management access',
                'level': 75,
                'is_system': True
            },
            {
                'name': 'Volunteer',
                'description': 'Library volunteer with operational access',
                'level': 50,
                'is_system': True
            },
            {
                'name': 'Student',
                'description': 'Student with basic library access',
                'level': 25,
                'is_system': True
            }
        ]
        
        created_roles = []
        for role_data in default_roles:
            existing_role = cls.get_by_name(role_data['name'])
            if not existing_role:
                role = cls(**role_data)
                db.session.add(role)
                created_roles.append(role)
        
        if created_roles:
            db.session.commit()
        
        return created_roles