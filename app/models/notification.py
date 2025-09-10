"""
Notification model for user notifications
"""
from datetime import datetime
from enum import Enum
from app import db


class NotificationType(Enum):
    """Notification type enumeration"""
    TRANSACTION_APPROVED = 'transaction_approved'
    TRANSACTION_REJECTED = 'transaction_rejected'
    TRANSACTION_ISSUED = 'transaction_issued'
    TRANSACTION_RETURNED = 'transaction_returned'
    TRANSACTION_OVERDUE = 'transaction_overdue'
    TRANSACTION_DUE_SOON = 'transaction_due_soon'
    RENEWAL_APPROVED = 'renewal_approved'
    RENEWAL_REJECTED = 'renewal_rejected'
    FINE_APPLIED = 'fine_applied'
    FINE_WAIVED = 'fine_waived'
    WAITLIST_AVAILABLE = 'waitlist_available'
    SYSTEM_ANNOUNCEMENT = 'system_announcement'


class NotificationPriority(Enum):
    """Notification priority levels"""
    LOW = 'low'
    NORMAL = 'normal'
    HIGH = 'high'
    URGENT = 'urgent'


class Notification(db.Model):
    """Notification model for user notifications"""
    __tablename__ = 'notification'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Recipient information
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Notification content
    type = db.Column(db.Enum(NotificationType), nullable=False)
    priority = db.Column(db.Enum(NotificationPriority), default=NotificationPriority.NORMAL, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    
    # Related entities (optional)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), nullable=True)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_item.id'), nullable=True)
    
    # Status tracking
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    read_at = db.Column(db.DateTime, nullable=True)
    
    # Delivery tracking
    is_sent = db.Column(db.Boolean, default=False, nullable=False)
    sent_at = db.Column(db.DateTime, nullable=True)
    delivery_method = db.Column(db.String(50), nullable=True)  # email, sms, push, in_app
    
    # Metadata
    data = db.Column(db.JSON, nullable=True)  # Additional structured data
    expires_at = db.Column(db.DateTime, nullable=True)  # Optional expiration
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = db.relationship('User', backref='notifications')
    transaction = db.relationship('Transaction', backref='notifications')
    item = db.relationship('InventoryItem', backref='notifications')
    
    # Indexes for performance
    __table_args__ = (
        db.Index('idx_notification_user', 'user_id'),
        db.Index('idx_notification_type', 'type'),
        db.Index('idx_notification_unread', 'user_id', 'is_read'),
        db.Index('idx_notification_created', 'created_at'),
        db.Index('idx_notification_transaction', 'transaction_id'),
        db.Index('idx_notification_priority', 'priority'),
        # Composite indexes for common queries
        db.Index('idx_notification_user_type', 'user_id', 'type'),
        db.Index('idx_notification_user_created', 'user_id', 'created_at'),
    )
    
    def __repr__(self):
        return f'<Notification {self.id} - {self.type.value} for User {self.user_id}>'
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()
    
    def mark_as_sent(self, delivery_method=None):
        """Mark notification as sent"""
        if not self.is_sent:
            self.is_sent = True
            self.sent_at = datetime.utcnow()
            self.delivery_method = delivery_method or 'in_app'
            self.updated_at = datetime.utcnow()
    
    def is_expired(self):
        """Check if notification has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self, include_user=False):
        """Convert notification to dictionary"""
        data = {
            'id': self.id,
            'type': self.type.value,
            'priority': self.priority.value,
            'title': self.title,
            'message': self.message,
            'is_read': self.is_read,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'is_sent': self.is_sent,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'delivery_method': self.delivery_method,
            'data': self.data,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_expired': self.is_expired()
        }
        
        if include_user and self.user:
            data['user'] = {
                'id': self.user.id,
                'name': self.user.name,
                'email': self.user.email
            }
        
        if self.transaction:
            data['transaction_id'] = self.transaction.transaction_id
        
        if self.item:
            data['item'] = {
                'id': self.item.id,
                'title': self.item.title
            }
        
        return data
    
    @classmethod
    def create_notification(
        cls, 
        user_id, 
        notification_type, 
        title, 
        message, 
        priority=NotificationPriority.NORMAL,
        transaction_id=None,
        item_id=None,
        data=None,
        expires_at=None
    ):
        """Create a new notification"""
        notification = cls(
            user_id=user_id,
            type=notification_type,
            priority=priority,
            title=title,
            message=message,
            transaction_id=transaction_id,
            item_id=item_id,
            data=data,
            expires_at=expires_at
        )
        
        db.session.add(notification)
        return notification
    
    @classmethod
    def get_user_notifications(cls, user_id, unread_only=False, limit=None):
        """Get notifications for a user"""
        query = cls.query.filter_by(user_id=user_id)
        
        if unread_only:
            query = query.filter_by(is_read=False)
        
        # Filter out expired notifications
        query = query.filter(
            db.or_(
                cls.expires_at.is_(None),
                cls.expires_at > datetime.utcnow()
            )
        )
        
        query = query.order_by(cls.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @classmethod
    def get_unread_count(cls, user_id):
        """Get count of unread notifications for a user"""
        return cls.query.filter_by(
            user_id=user_id,
            is_read=False
        ).filter(
            db.or_(
                cls.expires_at.is_(None),
                cls.expires_at > datetime.utcnow()
            )
        ).count()
    
    @classmethod
    def mark_all_as_read(cls, user_id):
        """Mark all notifications as read for a user"""
        notifications = cls.query.filter_by(
            user_id=user_id,
            is_read=False
        ).all()
        
        for notification in notifications:
            notification.mark_as_read()
        
        return len(notifications)
    
    @classmethod
    def cleanup_expired(cls):
        """Remove expired notifications"""
        expired_notifications = cls.query.filter(
            cls.expires_at.isnot(None),
            cls.expires_at <= datetime.utcnow()
        ).all()
        
        count = len(expired_notifications)
        for notification in expired_notifications:
            db.session.delete(notification)
        
        return count