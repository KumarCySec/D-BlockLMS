"""
Department model for organizational structure
"""
from datetime import datetime
from app import db


class Department(db.Model):
    """Department model for organizing users and inventory"""
    __tablename__ = 'department'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    code = db.Column(db.String(10), unique=True, nullable=False)  # e.g., 'CSE', 'ECE'
    description = db.Column(db.String(200), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        db.Index('idx_department_name', 'name'),
        db.Index('idx_department_code', 'code'),
        db.Index('idx_department_active', 'is_active'),
    )
    
    def __repr__(self):
        return f'<Department {self.name}>'
    
    def get_user_count(self):
        """Get number of users in this department"""
        return len(self.users)
    
    def get_active_users(self):
        """Get active users in this department"""
        from app.models.user import UserStatus
        return [user for user in self.users if user.status == UserStatus.ACTIVE]
    
    def get_volunteers(self):
        """Get volunteers in this department"""
        volunteers = []
        for user in self.get_active_users():
            if user.has_role('Volunteer'):
                volunteers.append(user)
        return volunteers
    
    def get_incharge(self):
        """Get incharge for this department"""
        for user in self.get_active_users():
            if user.has_role('Incharge'):
                return user
        return None
    
    def can_be_deleted(self):
        """Check if department can be deleted (no associated users or inventory)"""
        return self.get_user_count() == 0
    
    def to_dict(self, include_stats=False):
        """Convert department to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
        }
        
        if include_stats:
            data.update({
                'user_count': self.get_user_count(),
                'active_users': len(self.get_active_users()),
                'volunteers': len(self.get_volunteers()),
                'incharge': self.get_incharge().name if self.get_incharge() else None
            })
        
        return data
    
    @classmethod
    def get_by_name(cls, name):
        """Get department by name"""
        return cls.query.filter_by(name=name).first()
    
    @classmethod
    def get_by_code(cls, code):
        """Get department by code"""
        return cls.query.filter_by(code=code).first()
    
    @classmethod
    def get_active_departments(cls):
        """Get all active departments"""
        return cls.query.filter_by(is_active=True).order_by(cls.name).all()
    
    @classmethod
    def create_default_departments(cls):
        """Create default departments"""
        default_departments = [
            {'name': 'Computer Science Engineering', 'code': 'CSE', 'description': 'Computer Science and Engineering Department'},
            {'name': 'Electronics and Communication Engineering', 'code': 'ECE', 'description': 'Electronics and Communication Engineering Department'},
            {'name': 'Electrical and Electronics Engineering', 'code': 'EEE', 'description': 'Electrical and Electronics Engineering Department'},
            {'name': 'Civil Engineering', 'code': 'CIVIL', 'description': 'Civil Engineering Department'},
            {'name': 'Automobile Engineering', 'code': 'AUTO', 'description': 'Automobile Engineering Department'},
            {'name': 'Mechanical Engineering', 'code': 'MECH', 'description': 'Mechanical Engineering Department'},
            {'name': 'Information Technology', 'code': 'IT', 'description': 'Information Technology Department'}
        ]
        
        created_departments = []
        for dept_data in default_departments:
            existing_dept = cls.get_by_code(dept_data['code'])
            if not existing_dept:
                department = cls(**dept_data)
                db.session.add(department)
                created_departments.append(department)
        
        if created_departments:
            db.session.commit()
        
        return created_departments
    
    @classmethod
    def get_department_by_branch(cls, branch):
        """Map branch to department (for auto-linking during registration)"""
        branch_mapping = {
            'CSE': 'CSE',
            'Computer Science': 'CSE',
            'ECE': 'ECE',
            'Electronics': 'ECE',
            'EEE': 'EEE',
            'Electrical': 'EEE',
            'Civil': 'CIVIL',
            'Civil Engineering': 'CIVIL',
            'Automobile': 'AUTO',
            'Auto': 'AUTO',
            'Mechanical': 'MECH',
            'Mech': 'MECH',
            'IT': 'IT',
            'Information Technology': 'IT'
        }
        
        code = branch_mapping.get(branch)
        if code:
            return cls.get_by_code(code)
        return None