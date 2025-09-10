"""
Waitlist model for managing item availability queues
"""
from datetime import datetime, timedelta
from enum import Enum
from app import db
from sqlalchemy import func


class WaitlistStatus(Enum):
    """Waitlist request status enumeration"""
    ACTIVE = 'active'
    NOTIFIED = 'notified'
    EXPIRED = 'expired'
    CLAIMED = 'claimed'
    CANCELLED = 'cancelled'


class WaitlistRequest(db.Model):
    """Waitlist request model with FIFO queue management"""
    __tablename__ = 'waitlist_request'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_item.id'), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Enum(WaitlistStatus), default=WaitlistStatus.ACTIVE, nullable=False)
    
    # Notification and claim tracking
    notified_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)  # 24-hour claim window
    claimed_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    
    # Metadata
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = db.relationship('User', backref='waitlist_requests')
    item = db.relationship('InventoryItem', backref='waitlist_requests')
    
    # Indexes for performance
    __table_args__ = (
        db.Index('idx_waitlist_item_pos', 'item_id', 'position'),
        db.Index('idx_waitlist_user', 'user_id'),
        db.Index('idx_waitlist_status', 'status'),
        db.Index('idx_waitlist_expires', 'expires_at'),
        db.UniqueConstraint('user_id', 'item_id', name='unique_user_item_waitlist')
    )
    
    def __repr__(self):
        return f'<WaitlistRequest {self.user_id} for item {self.item_id} (pos: {self.position})>'
    
    def notify_availability(self, claim_hours=24):
        """Notify user that item is available and set claim window"""
        if self.status != WaitlistStatus.ACTIVE:
            raise ValueError(f"Cannot notify waitlist request with status {self.status.value}")
        
        self.status = WaitlistStatus.NOTIFIED
        self.notified_at = datetime.utcnow()
        self.expires_at = datetime.utcnow() + timedelta(hours=claim_hours)
        self.updated_at = datetime.utcnow()
        
        # Send notification
        try:
            from app.models.notification import Notification, NotificationType
            Notification.create_notification(
                user_id=self.user_id,
                notification_type=NotificationType.WAITLIST_AVAILABLE,
                title="Item Available",
                message=f"'{self.item.title}' is now available! You have {claim_hours} hours to claim it.",
                item_id=self.item_id,
                waitlist_id=self.id
            )
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Failed to send waitlist notification: {e}")
        
        # Log the notification
        from app.models.audit_log import AuditLog, AuditAction
        AuditLog.log_action(
            action=AuditAction.WAITLIST_NOTIFY,
            description=f"Waitlist notification sent for item {self.item.title}",
            target_type='WaitlistRequest',
            target_id=self.id,
            target_identifier=f"waitlist-{self.id}",
            metadata={
                'user_id': self.user_id,
                'item_id': self.item_id,
                'position': self.position,
                'expires_at': self.expires_at.isoformat()
            }
        )
        
        return True
    
    def claim_item(self):
        """Mark item as claimed by user"""
        if self.status != WaitlistStatus.NOTIFIED:
            raise ValueError(f"Cannot claim item with waitlist status {self.status.value}")
        
        if self.expires_at and datetime.utcnow() > self.expires_at:
            self.expire_claim()
            raise ValueError("Claim window has expired")
        
        self.status = WaitlistStatus.CLAIMED
        self.claimed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        # Log the claim
        from app.models.audit_log import AuditLog, AuditAction
        AuditLog.log_action(
            action=AuditAction.WAITLIST_CLAIM,
            description=f"Waitlist item claimed for {self.item.title}",
            target_type='WaitlistRequest',
            target_id=self.id,
            target_identifier=f"waitlist-{self.id}",
            metadata={
                'user_id': self.user_id,
                'item_id': self.item_id,
                'position': self.position
            }
        )
        
        return True
    
    def expire_claim(self):
        """Mark claim as expired and notify next in queue"""
        if self.status != WaitlistStatus.NOTIFIED:
            return False
        
        self.status = WaitlistStatus.EXPIRED
        self.updated_at = datetime.utcnow()
        
        # Notify next person in queue
        next_request = WaitlistRequest.get_next_in_queue(self.item_id)
        if next_request:
            next_request.notify_availability()
        
        # Log the expiration
        from app.models.audit_log import AuditLog, AuditAction
        AuditLog.log_action(
            action=AuditAction.WAITLIST_EXPIRE,
            description=f"Waitlist claim expired for {self.item.title}",
            target_type='WaitlistRequest',
            target_id=self.id,
            target_identifier=f"waitlist-{self.id}",
            metadata={
                'user_id': self.user_id,
                'item_id': self.item_id,
                'position': self.position
            }
        )
        
        return True
    
    def cancel_request(self, reason=None):
        """Cancel waitlist request"""
        if self.status in [WaitlistStatus.CLAIMED, WaitlistStatus.EXPIRED]:
            raise ValueError(f"Cannot cancel waitlist request with status {self.status.value}")
        
        old_position = self.position
        self.status = WaitlistStatus.CANCELLED
        self.cancelled_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        if reason:
            self.notes = reason
        
        # Update positions for remaining requests
        WaitlistRequest.query.filter(
            WaitlistRequest.item_id == self.item_id,
            WaitlistRequest.position > old_position,
            WaitlistRequest.status == WaitlistStatus.ACTIVE
        ).update({
            WaitlistRequest.position: WaitlistRequest.position - 1
        })
        
        # Log the cancellation
        from app.models.audit_log import AuditLog, AuditAction
        AuditLog.log_action(
            action=AuditAction.WAITLIST_CANCEL,
            description=f"Waitlist request cancelled for {self.item.title}",
            target_type='WaitlistRequest',
            target_id=self.id,
            target_identifier=f"waitlist-{self.id}",
            metadata={
                'user_id': self.user_id,
                'item_id': self.item_id,
                'old_position': old_position,
                'reason': reason
            }
        )
        
        return True
    
    def get_estimated_wait_time(self):
        """Estimate wait time based on position and average return time"""
        if self.status != WaitlistStatus.ACTIVE:
            return None
        
        # Simple estimation: position * average loan period (7 days)
        # In a real system, this could be more sophisticated
        estimated_days = self.position * 7
        return estimated_days
    
    def to_dict(self, include_user=False, include_item=False):
        """Convert waitlist request to dictionary"""
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'item_id': self.item_id,
            'position': self.position,
            'status': self.status.value,
            'notified_at': self.notified_at.isoformat() if self.notified_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'claimed_at': self.claimed_at.isoformat() if self.claimed_at else None,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'estimated_wait_days': self.get_estimated_wait_time()
        }
        
        if include_user and self.user:
            data['user'] = {
                'id': self.user.id,
                'name': self.user.name,
                'roll_number': self.user.roll_number,
                'email': self.user.email
            }
        
        if include_item and self.item:
            data['item'] = {
                'id': self.item.id,
                'title': self.item.title,
                'authors': self.item.authors,
                'item_type': self.item.item_type.value
            }
        
        return data
    
    @classmethod
    def join_waitlist(cls, user_id, item_id, notes=None):
        """Add user to waitlist for an item"""
        # Check if user is already in waitlist for this item
        existing = cls.query.filter_by(
            user_id=user_id,
            item_id=item_id,
            status=WaitlistStatus.ACTIVE
        ).first()
        
        if existing:
            raise ValueError("User is already in waitlist for this item")
        
        # Check if user already has this item borrowed
        from app.models.transaction import Transaction, TransactionStatus
        active_transaction = Transaction.query.filter_by(
            user_id=user_id,
            item_id=item_id,
            status=TransactionStatus.BORROWED
        ).first()
        
        if active_transaction:
            raise ValueError("User already has this item borrowed")
        
        # Get next position in queue
        max_position = db.session.query(func.max(cls.position)).filter_by(
            item_id=item_id,
            status=WaitlistStatus.ACTIVE
        ).scalar() or 0
        
        next_position = max_position + 1
        
        # Create waitlist request
        waitlist_request = cls(
            user_id=user_id,
            item_id=item_id,
            position=next_position,
            status=WaitlistStatus.ACTIVE,
            notes=notes
        )
        
        db.session.add(waitlist_request)
        
        # Log the join
        from app.models.audit_log import AuditLog, AuditAction
        AuditLog.log_action(
            action=AuditAction.WAITLIST_JOIN,
            description=f"User joined waitlist for item {item_id}",
            target_type='WaitlistRequest',
            target_id=waitlist_request.id,
            target_identifier=f"waitlist-{waitlist_request.id}",
            metadata={
                'user_id': user_id,
                'item_id': item_id,
                'position': next_position,
                'notes': notes
            }
        )
        
        return waitlist_request
    
    @classmethod
    def get_user_waitlist(cls, user_id, status=None):
        """Get waitlist requests for a user"""
        query = cls.query.filter_by(user_id=user_id)
        
        if status:
            if isinstance(status, list):
                query = query.filter(cls.status.in_([WaitlistStatus(s) for s in status]))
            else:
                query = query.filter_by(status=WaitlistStatus(status))
        
        return query.order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_item_waitlist(cls, item_id, status=None):
        """Get waitlist for an item"""
        query = cls.query.filter_by(item_id=item_id)
        
        if status:
            if isinstance(status, list):
                query = query.filter(cls.status.in_([WaitlistStatus(s) for s in status]))
            else:
                query = query.filter_by(status=WaitlistStatus(status))
        
        return query.order_by(cls.position.asc()).all()
    
    @classmethod
    def get_next_in_queue(cls, item_id):
        """Get next active request in queue for an item"""
        return cls.query.filter_by(
            item_id=item_id,
            status=WaitlistStatus.ACTIVE
        ).order_by(cls.position.asc()).first()
    
    @classmethod
    def get_expired_claims(cls):
        """Get all expired claims that need processing"""
        return cls.query.filter(
            cls.status == WaitlistStatus.NOTIFIED,
            cls.expires_at < datetime.utcnow()
        ).all()
    
    @classmethod
    def process_item_return(cls, item_id):
        """Process waitlist when an item is returned"""
        # Get next person in queue
        next_request = cls.get_next_in_queue(item_id)
        
        if next_request:
            # Notify them that item is available
            next_request.notify_availability()
            return next_request
        
        return None
    
    @classmethod
    def get_waitlist_statistics(cls, item_id=None):
        """Get waitlist statistics"""
        query = cls.query
        
        if item_id:
            query = query.filter_by(item_id=item_id)
        
        total_requests = query.count()
        active_requests = query.filter_by(status=WaitlistStatus.ACTIVE).count()
        notified_requests = query.filter_by(status=WaitlistStatus.NOTIFIED).count()
        
        # Average wait time (simplified)
        avg_position = db.session.query(func.avg(cls.position)).filter_by(
            status=WaitlistStatus.ACTIVE
        ).scalar() or 0
        
        return {
            'total_requests': total_requests,
            'active_requests': active_requests,
            'notified_requests': notified_requests,
            'average_position': float(avg_position),
            'estimated_avg_wait_days': float(avg_position) * 7
        }
    
    @classmethod
    def cleanup_expired_claims(cls):
        """Cleanup expired claims and notify next in queue"""
        expired_claims = cls.get_expired_claims()
        processed_items = set()
        
        for claim in expired_claims:
            claim.expire_claim()
            processed_items.add(claim.item_id)
        
        db.session.commit()
        
        return len(expired_claims), len(processed_items)