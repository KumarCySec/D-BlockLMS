"""
Inventory Item model for library items management
"""
from datetime import datetime
from enum import Enum
from app import db


class ItemType(Enum):
    """Item type enumeration"""
    BOOK = 'book'
    LAPTOP = 'laptop'
    KIT = 'kit'


class InventoryItem(db.Model):
    """Inventory item model for books, laptops, and kits"""
    __tablename__ = 'inventory_item'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Item identification
    item_type = db.Column(db.Enum(ItemType), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    authors = db.Column(db.String(200), nullable=True)  # For books
    language = db.Column(db.String(50), nullable=True)
    published_date = db.Column(db.Date, nullable=True)
    sku_code = db.Column(db.String(50), unique=True, nullable=True)
    description = db.Column(db.Text, nullable=True)
    
    # Donor information
    donor_id = db.Column(db.Integer, db.ForeignKey('donor.id'), nullable=False)
    date_of_donation = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    
    # Quantity tracking
    total_quantity = db.Column(db.Integer, nullable=False, default=1)
    available_quantity = db.Column(db.Integer, nullable=False, default=1)
    
    # Department association (optional)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    donor = db.relationship('Donor', backref='donated_items')
    department = db.relationship('Department', backref='inventory_items')
    
    # Indexes for search and filtering
    __table_args__ = (
        db.Index('idx_inventory_type', 'item_type'),
        db.Index('idx_inventory_title', 'title'),
        db.Index('idx_inventory_authors', 'authors'),
        db.Index('idx_inventory_language', 'language'),
        db.Index('idx_inventory_donor', 'donor_id'),
        db.Index('idx_inventory_department', 'department_id'),
        db.Index('idx_inventory_availability', 'available_quantity'),
        db.Index('idx_inventory_created', 'created_at'),
        # Composite indexes for common queries
        db.Index('idx_inventory_type_availability', 'item_type', 'available_quantity'),
        db.Index('idx_inventory_dept_type', 'department_id', 'item_type'),
    )
    
    def __repr__(self):
        return f'<InventoryItem {self.title} ({self.item_type.value})>'
    
    def is_available(self):
        """Check if item is available for checkout"""
        return self.available_quantity > 0
    
    def get_borrowed_count(self):
        """Get number of items currently borrowed"""
        return self.total_quantity - self.available_quantity
    
    def update_availability(self, quantity_change):
        """Update available quantity atomically"""
        new_quantity = self.available_quantity + quantity_change
        
        # Validate quantity constraints
        if new_quantity < 0:
            raise ValueError("Available quantity cannot be negative")
        if new_quantity > self.total_quantity:
            raise ValueError("Available quantity cannot exceed total quantity")
        
        self.available_quantity = new_quantity
        self.updated_at = datetime.utcnow()
        return True
    
    def get_popularity_score(self):
        """Calculate popularity score based on transaction history"""
        # This would be calculated from transaction history
        # For now, return a simple metric based on borrowed count
        if self.total_quantity == 0:
            return 0
        return (self.total_quantity - self.available_quantity) / self.total_quantity
    
    def to_dict(self, include_donor=True, include_stats=False):
        """Convert inventory item to dictionary"""
        data = {
            'id': self.id,
            'item_type': self.item_type.value,
            'title': self.title,
            'authors': self.authors,
            'language': self.language,
            'published_date': self.published_date.isoformat() if self.published_date else None,
            'sku_code': self.sku_code,
            'description': self.description,
            'total_quantity': self.total_quantity,
            'available_quantity': self.available_quantity,
            'is_available': self.is_available(),
            'department_id': self.department_id,
            'department_name': self.department.name if self.department else None,
            'date_of_donation': self.date_of_donation.isoformat(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if include_donor and self.donor:
            data['donor'] = {
                'id': self.donor.id,
                'name': self.donor.name,
                'branch': self.donor.branch,
                'batch': self.donor.batch
            }
        
        if include_stats:
            data.update({
                'borrowed_count': self.get_borrowed_count(),
                'popularity_score': self.get_popularity_score()
            })
        
        return data
    
    @classmethod
    def search_items(cls, query=None, filters=None, sort_by='title', sort_order='asc', 
                    limit=None, offset=None):
        """
        Advanced search with filtering and sorting
        
        Args:
            query: Text search query
            filters: Dict with filter criteria
            sort_by: Sort field (title, authors, created_at, popularity, availability)
            sort_order: Sort order (asc, desc)
            limit: Maximum results
            offset: Results offset for pagination
        """
        query_obj = cls.query
        
        # Text search across multiple fields
        if query:
            search_filter = f"%{query}%"
            query_obj = query_obj.filter(
                db.or_(
                    cls.title.ilike(search_filter),
                    cls.authors.ilike(search_filter),
                    cls.description.ilike(search_filter),
                    cls.sku_code.ilike(search_filter)
                )
            )
        
        # Apply filters
        if filters:
            if filters.get('item_type'):
                query_obj = query_obj.filter(cls.item_type == ItemType(filters['item_type']))
            
            if filters.get('language'):
                query_obj = query_obj.filter(cls.language == filters['language'])
            
            if filters.get('department_id'):
                query_obj = query_obj.filter(cls.department_id == filters['department_id'])
            
            if filters.get('donor_id'):
                query_obj = query_obj.filter(cls.donor_id == filters['donor_id'])
            
            if filters.get('availability') == 'available':
                query_obj = query_obj.filter(cls.available_quantity > 0)
            elif filters.get('availability') == 'unavailable':
                query_obj = query_obj.filter(cls.available_quantity == 0)
            
            if filters.get('donor_batch'):
                query_obj = query_obj.join(cls.donor).filter(
                    db.text("donor.batch = :batch")
                ).params(batch=filters['donor_batch'])
            
            if filters.get('donor_branch'):
                query_obj = query_obj.join(cls.donor).filter(
                    db.text("donor.branch = :branch")
                ).params(branch=filters['donor_branch'])
        
        # Apply sorting
        if sort_by == 'title':
            sort_column = cls.title
        elif sort_by == 'authors':
            sort_column = cls.authors
        elif sort_by == 'created_at' or sort_by == 'date_added':
            sort_column = cls.created_at
        elif sort_by == 'availability':
            sort_column = cls.available_quantity
        elif sort_by == 'popularity':
            # Sort by borrowed count (total - available)
            sort_column = (cls.total_quantity - cls.available_quantity)
        else:
            sort_column = cls.title
        
        if sort_order == 'desc':
            query_obj = query_obj.order_by(sort_column.desc())
        else:
            query_obj = query_obj.order_by(sort_column.asc())
        
        # Add secondary sort by title for consistency
        if sort_by != 'title':
            query_obj = query_obj.order_by(cls.title.asc())
        
        # Apply pagination
        if offset:
            query_obj = query_obj.offset(offset)
        
        if limit:
            query_obj = query_obj.limit(limit)
        
        return query_obj.all()
    
    @classmethod
    def get_filter_options(cls):
        """Get available filter options for UI"""
        # Get unique values for filters
        item_types = [item_type.value for item_type in ItemType]
        
        languages = db.session.query(cls.language.distinct()).filter(
            cls.language.isnot(None)
        ).all()
        languages = [lang[0] for lang in languages if lang[0]]
        
        # Get departments with inventory
        departments = db.session.query(
            cls.department_id, 
            db.text("department.name")
        ).join(
            db.text("department"), 
            db.text("inventory_item.department_id = department.id")
        ).distinct().all()
        
        return {
            'item_types': item_types,
            'languages': sorted(languages),
            'departments': [{'id': dept[0], 'name': dept[1]} for dept in departments],
            'sort_options': [
                {'value': 'title', 'label': 'Title'},
                {'value': 'authors', 'label': 'Author'},
                {'value': 'created_at', 'label': 'Date Added'},
                {'value': 'popularity', 'label': 'Popularity'},
                {'value': 'availability', 'label': 'Availability'}
            ]
        }
    
    @classmethod
    def get_popular_items(cls, limit=10):
        """Get most popular items by borrow count"""
        return cls.query.order_by(
            (cls.total_quantity - cls.available_quantity).desc()
        ).limit(limit).all()
    
    @classmethod
    def get_recent_additions(cls, limit=10):
        """Get recently added items"""
        return cls.query.order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_by_sku(cls, sku_code):
        """Get item by SKU code"""
        return cls.query.filter_by(sku_code=sku_code).first()
    
    @classmethod
    def get_available_items(cls, item_type=None, department_id=None):
        """Get available items with optional filters"""
        query_obj = cls.query.filter(cls.available_quantity > 0)
        
        if item_type:
            query_obj = query_obj.filter(cls.item_type == ItemType(item_type))
        
        if department_id:
            query_obj = query_obj.filter(cls.department_id == department_id)
        
        return query_obj.order_by(cls.title).all()