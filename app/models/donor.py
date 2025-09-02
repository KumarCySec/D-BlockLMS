"""
Donor model for alumni donation tracking
"""
from datetime import datetime
from app import db


class Donor(db.Model):
    """Donor model for tracking alumni donations"""
    __tablename__ = 'donor'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Required donor information
    name = db.Column(db.String(100), nullable=False)
    branch = db.Column(db.String(50), nullable=False)
    batch = db.Column(db.String(10), nullable=False)
    
    # Optional contact information
    address = db.Column(db.Text, nullable=True)
    phone = db.Column(db.String(15), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    
    # Additional information
    notes = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        db.Index('idx_donor_name', 'name'),
        db.Index('idx_donor_branch', 'branch'),
        db.Index('idx_donor_batch', 'batch'),
        db.Index('idx_donor_email', 'email'),
    )
    
    def __repr__(self):
        return f'<Donor {self.name} ({self.batch})>'
    
    def get_donation_count(self):
        """Get number of items donated by this donor"""
        return len(self.donated_items)
    
    def get_total_quantity_donated(self):
        """Get total quantity of items donated"""
        return sum(item.total_quantity for item in self.donated_items)
    
    def get_donations_by_type(self):
        """Get donations grouped by item type"""
        from collections import defaultdict
        donations = defaultdict(int)
        
        for item in self.donated_items:
            donations[item.item_type.value] += item.total_quantity
        
        return dict(donations)
    
    def to_dict(self, include_stats=False):
        """Convert donor to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'branch': self.branch,
            'batch': self.batch,
            'address': self.address,
            'phone': self.phone,
            'email': self.email,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if include_stats:
            data.update({
                'donation_count': self.get_donation_count(),
                'total_quantity': self.get_total_quantity_donated(),
                'donations_by_type': self.get_donations_by_type()
            })
        
        return data
    
    @classmethod
    def search_donors(cls, query=None, branch=None, batch=None, limit=None, offset=None):
        """Search donors with filters"""
        query_obj = cls.query
        
        if query:
            search_filter = f"%{query}%"
            query_obj = query_obj.filter(
                db.or_(
                    cls.name.ilike(search_filter),
                    cls.email.ilike(search_filter),
                    cls.notes.ilike(search_filter)
                )
            )
        
        if branch:
            query_obj = query_obj.filter(cls.branch == branch)
        
        if batch:
            query_obj = query_obj.filter(cls.batch == batch)
        
        # Order by name
        query_obj = query_obj.order_by(cls.name)
        
        if offset:
            query_obj = query_obj.offset(offset)
        
        if limit:
            query_obj = query_obj.limit(limit)
        
        return query_obj.all()
    
    @classmethod
    def get_by_email(cls, email):
        """Get donor by email"""
        return cls.query.filter_by(email=email).first()
    
    @classmethod
    def get_top_donors(cls, limit=10):
        """Get top donors by quantity donated"""
        # This would require a more complex query in production
        # For now, return all donors ordered by creation date
        return cls.query.order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_branches(cls):
        """Get unique branches from donors"""
        return [row[0] for row in db.session.query(cls.branch.distinct()).all()]
    
    @classmethod
    def get_batches(cls):
        """Get unique batches from donors"""
        return [row[0] for row in db.session.query(cls.batch.distinct()).order_by(cls.batch.desc()).all()]