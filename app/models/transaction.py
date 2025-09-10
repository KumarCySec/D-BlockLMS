"""
Transaction model for checkout/return workflow management
"""
from datetime import datetime, timedelta
from enum import Enum
from decimal import Decimal
from app import db
from sqlalchemy import func


class TransactionStatus(Enum):
    """Transaction status enumeration with state machine implementation"""
    REQUESTED = 'requested'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    BORROWED = 'borrowed'
    RETURNED = 'returned'
    OVERDUE = 'overdue'
    CANCELLED = 'cancelled'


class TransactionCounter(db.Model):
    """Counter for generating unique transaction IDs"""
    __tablename__ = 'transaction_counter'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)
    counter = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        db.Index('idx_transaction_counter_date', 'date'),
    )
    
    @classmethod
    def generate_transaction_id(cls, date=None):
        """Generate transaction ID with format DBL-YYYYMMDD-XXXX as per Requirement 4.3"""
        if date is None:
            date = datetime.now().date()
        
        # Use database-level locking for atomicity
        counter_record = cls.query.filter_by(date=date).with_for_update().first()
        
        if not counter_record:
            counter_record = cls(date=date, counter=1)
            db.session.add(counter_record)
        else:
            counter_record.counter += 1
            counter_record.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Format: DBL-YYYYMMDD-XXXX (as per Requirement 4.3)
        date_str = date.strftime('%Y%m%d')
        return f"DBL-{date_str}-{counter_record.counter:04d}"


class Transaction(db.Model):
    """Transaction model with state machine implementation"""
    __tablename__ = 'transaction'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(20), unique=True, nullable=False)
    
    # Core relationships
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_item.id'), nullable=False)
    
    # Status and workflow
    status = db.Column(db.Enum(TransactionStatus), nullable=False, default=TransactionStatus.REQUESTED)
    
    # Timestamps for workflow tracking
    requested_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    approved_at = db.Column(db.DateTime, nullable=True)
    issued_at = db.Column(db.DateTime, nullable=True)
    due_date = db.Column(db.DateTime, nullable=True)
    returned_at = db.Column(db.DateTime, nullable=True)
    
    # Approval tracking
    approved_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    
    # Renewal tracking
    renew_count = db.Column(db.Integer, default=0, nullable=False)
    max_renewals = db.Column(db.Integer, default=4, nullable=False)  # Configurable per transaction
    
    # Fine tracking
    fine_accumulated = db.Column(db.Numeric(10, 2), default=Decimal('0.00'), nullable=False)
    fine_waived = db.Column(db.Boolean, default=False, nullable=False)
    fine_waived_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    fine_waived_reason = db.Column(db.Text, nullable=True)
    
    # Additional notes and metadata
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='transactions')
    item = db.relationship('InventoryItem', backref='transactions')
    approver = db.relationship('User', foreign_keys=[approved_by_user_id])
    fine_waiver = db.relationship('User', foreign_keys=[fine_waived_by])
    
    # Indexes for performance
    __table_args__ = (
        db.Index('idx_transaction_id', 'transaction_id'),
        db.Index('idx_transaction_user', 'user_id'),
        db.Index('idx_transaction_item', 'item_id'),
        db.Index('idx_transaction_status', 'status'),
        db.Index('idx_transaction_due_date', 'due_date'),
        db.Index('idx_transaction_requested', 'requested_at'),
        db.Index('idx_transaction_approver', 'approved_by_user_id'),
        # Composite indexes for common queries
        db.Index('idx_transaction_user_status', 'user_id', 'status'),
        db.Index('idx_transaction_item_status', 'item_id', 'status'),
        db.Index('idx_transaction_status_due', 'status', 'due_date'),
    )
    
    def __repr__(self):
        return f'<Transaction {self.transaction_id} - {self.status.value}>'
    
    # State machine validation
    VALID_TRANSITIONS = {
        TransactionStatus.REQUESTED: [TransactionStatus.APPROVED, TransactionStatus.REJECTED, TransactionStatus.CANCELLED],
        TransactionStatus.APPROVED: [TransactionStatus.BORROWED, TransactionStatus.CANCELLED],
        TransactionStatus.BORROWED: [TransactionStatus.RETURNED, TransactionStatus.OVERDUE],
        TransactionStatus.OVERDUE: [TransactionStatus.RETURNED],
        TransactionStatus.RETURNED: [],  # Terminal state
        TransactionStatus.REJECTED: [],  # Terminal state
        TransactionStatus.CANCELLED: []  # Terminal state
    }
    
    def can_transition_to(self, new_status):
        """Check if transition to new status is valid"""
        return new_status in self.VALID_TRANSITIONS.get(self.status, [])
    
    def transition_to(self, new_status, actor_id=None, notes=None):
        """Safely transition to new status with validation"""
        if not self.can_transition_to(new_status):
            raise ValueError(f"Invalid transition from {self.status.value} to {new_status.value}")
        
        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.utcnow()
        
        # Update relevant timestamps
        if new_status == TransactionStatus.APPROVED:
            self.approved_at = datetime.utcnow()
            self.approved_by_user_id = actor_id
            # Set due date (default 7 days from approval)
            self.due_date = datetime.utcnow() + timedelta(days=7)
            # Send notification
            try:
                from app.models.notification import Notification, NotificationType
                from app.models.inventory_item import InventoryItem
                item = InventoryItem.query.get(self.item_id)
                Notification.create_notification(
                    user_id=self.user_id,
                    notification_type=NotificationType.TRANSACTION_APPROVED,
                    title="Request Approved",
                    message=f"Your request for '{item.title}' has been approved. Please collect it from the library.",
                    transaction_id=self.id
                )
                db.session.commit()
            except Exception as e:
                from flask import current_app
                current_app.logger.error(f"Failed to send approval notification: {e}")
        elif new_status == TransactionStatus.BORROWED:
            self.issued_at = datetime.utcnow()
            # Send notification
            try:
                from app.models.notification import Notification, NotificationType
                from app.models.inventory_item import InventoryItem
                item = InventoryItem.query.get(self.item_id)
                Notification.create_notification(
                    user_id=self.user_id,
                    notification_type=NotificationType.TRANSACTION_ISSUED,
                    title="Item Issued",
                    message=f"'{item.title}' has been issued to you. Due date: {self.due_date.strftime('%Y-%m-%d')}",
                    transaction_id=self.id
                )
                db.session.commit()
            except Exception as e:
                from flask import current_app
                current_app.logger.error(f"Failed to send issued notification: {e}")
        elif new_status == TransactionStatus.RETURNED:
            self.returned_at = datetime.utcnow()
            # Send notification
            try:
                from app.models.notification import Notification, NotificationType
                from app.models.inventory_item import InventoryItem
                item = InventoryItem.query.get(self.item_id)
                message = f"'{item.title}' has been returned successfully."
                if self.fine_accumulated > 0 and not self.fine_waived:
                    message += f" Fine: ₹{self.fine_accumulated}"
                Notification.create_notification(
                    user_id=self.user_id,
                    notification_type=NotificationType.TRANSACTION_RETURNED,
                    title="Item Returned",
                    message=message,
                    transaction_id=self.id
                )
                db.session.commit()
            except Exception as e:
                from flask import current_app
                current_app.logger.error(f"Failed to send return notification: {e}")
        elif new_status == TransactionStatus.REJECTED:
            self.rejection_reason = notes
            # Send notification
            try:
                from app.models.notification import Notification, NotificationType
                from app.models.inventory_item import InventoryItem
                item = InventoryItem.query.get(self.item_id)
                message = f"Your request for '{item.title}' has been rejected."
                if notes:
                    message += f" Reason: {notes}"
                Notification.create_notification(
                    user_id=self.user_id,
                    notification_type=NotificationType.TRANSACTION_REJECTED,
                    title="Request Rejected",
                    message=message,
                    transaction_id=self.id
                )
                db.session.commit()
            except Exception as e:
                from flask import current_app
                current_app.logger.error(f"Failed to send rejection notification: {e}")
        
        if notes:
            self.notes = notes
        
        # Log the transition in audit log
        from app.models.audit_log import AuditLog, AuditAction
        AuditLog.log_action(
            action=AuditAction.CHECKOUT_APPROVE if new_status == TransactionStatus.APPROVED else AuditAction.CHECKOUT_REJECT if new_status == TransactionStatus.REJECTED else AuditAction.RETURN_PROCESS,
            description=f"Transaction {self.transaction_id} status changed from {old_status.value} to {new_status.value}",
            target_type='Transaction',
            target_id=self.id,
            target_identifier=self.transaction_id,
            metadata={
                'transaction_id': self.transaction_id,
                'old_status': old_status.value,
                'new_status': new_status.value,
                'notes': notes,
                'actor_id': actor_id
            }
        )
        
        return True
    
    def is_overdue(self):
        """Check if transaction is overdue"""
        if not self.due_date or self.status != TransactionStatus.BORROWED:
            return False
        return datetime.utcnow() > self.due_date
    
    def days_overdue(self):
        """Calculate days overdue"""
        if not self.is_overdue():
            return 0
        return (datetime.utcnow() - self.due_date).days
    
    def can_renew(self):
        """Check if transaction can be renewed"""
        if self.status != TransactionStatus.BORROWED:
            return False, "Item not currently borrowed"
        
        if self.renew_count >= self.max_renewals:
            return False, f"Maximum renewals ({self.max_renewals}) reached"
        
        # Check if item has waitlist (would need waitlist model)
        # For now, assume renewal is allowed
        return True, "Renewal allowed"
    
    def request_renewal(self, days=7):
        """Request renewal for the transaction"""
        can_renew, reason = self.can_renew()
        if not can_renew:
            raise ValueError(reason)
        
        # Extend due date
        self.due_date = self.due_date + timedelta(days=days)
        self.renew_count += 1
        self.updated_at = datetime.utcnow()
        
        return True
    
    def calculate_fine(self, daily_rate=Decimal('1.00')):
        """Calculate accumulated fine based on overdue days"""
        if not self.is_overdue():
            return Decimal('0.00')
        
        days_overdue = self.days_overdue()
        calculated_fine = days_overdue * daily_rate
        
        # Update accumulated fine
        self.fine_accumulated = calculated_fine
        return calculated_fine
    
    def waive_fine(self, waiver_user_id, reason=None):
        """Waive accumulated fine"""
        self.fine_waived = True
        self.fine_waived_by = waiver_user_id
        self.fine_waived_reason = reason
        self.updated_at = datetime.utcnow()
        
        # Log fine waiver
        from app.models.audit_log import AuditLog, AuditAction
        AuditLog.log_action(
            action=AuditAction.FINE_WAIVE,
            description=f"Fine waived for transaction {self.transaction_id}",
            target_type='Transaction',
            target_id=self.id,
            target_identifier=self.transaction_id,
            metadata={
                'transaction_id': self.transaction_id,
                'fine_amount': str(self.fine_accumulated),
                'reason': reason,
                'waiver_user_id': waiver_user_id
            }
        )
    
    def to_dict(self, include_user=True, include_item=True, include_approver=False):
        """Convert transaction to dictionary"""
        data = {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'user_id': self.user_id,
            'item_id': self.item_id,
            'status': self.status.value,
            'notes': self.notes,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'approved_by_user_id': self.approved_by_user_id,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'issued_at': self.issued_at.isoformat() if self.issued_at else None,
            'returned_at': self.returned_at.isoformat() if self.returned_at else None,
            'renew_count': self.renew_count,
            'fine_accumulated': str(self.fine_accumulated),
            'fine_waived': self.fine_waived,
            'fine_waived_by': self.fine_waived_by,
            'fine_waived_reason': self.fine_waived_reason,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'days_overdue': self.days_overdue(),
            'is_overdue': self.is_overdue()
        }
        
        if include_user and self.user:
            data['user'] = {
                'id': self.user.id,
                'name': self.user.name,
                'roll_number': self.user.roll_number,
                'email': self.user.email,
                'department': self.user.department.name if self.user.department else None
            }
        
        if include_item and self.item:
            data['item'] = {
                'id': self.item.id,
                'title': self.item.title,
                'authors': self.item.authors,
                'item_type': self.item.item_type.value,
                'sku_code': self.item.sku_code
            }
        
        if include_approver and self.approver:
            data['approver'] = {
                'id': self.approver.id,
                'name': self.approver.name,
                'roles': [role.name for role in self.approver.roles]
            }
        
        return data
    
    @classmethod
    def create_request(cls, user_id, item_id, notes=None):
        """Create a new checkout request"""
        # Generate unique transaction ID
        transaction_id = TransactionCounter.generate_transaction_id()
        
        transaction = cls(
            transaction_id=transaction_id,
            user_id=user_id,
            item_id=item_id,
            status=TransactionStatus.REQUESTED,
            notes=notes
        )
        
        db.session.add(transaction)
        
        # Note: Audit log will be created after commit in the service layer
        
        return transaction
    
    @classmethod
    def get_pending_approvals(cls, department_id=None, approver_roles=None):
        """Get transactions pending approval"""
        query = cls.query.filter_by(status=TransactionStatus.REQUESTED)
        
        if department_id:
            # Filter by user's department
            query = query.join(cls.user).filter_by(department_id=department_id)
        
        return query.order_by(cls.requested_at.asc()).all()
    
    @classmethod
    def get_user_transactions(cls, user_id, status=None, limit=None):
        """Get transactions for a specific user"""
        query = cls.query.filter_by(user_id=user_id)
        
        if status:
            if isinstance(status, list):
                query = query.filter(cls.status.in_([TransactionStatus(s) for s in status]))
            else:
                query = query.filter_by(status=TransactionStatus(status))
        
        query = query.order_by(cls.requested_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @classmethod
    def get_overdue_transactions(cls):
        """Get all overdue transactions"""
        return cls.query.filter(
            cls.status == TransactionStatus.BORROWED,
            cls.due_date < datetime.utcnow()
        ).all()
    
    @classmethod
    def get_due_soon(cls, days=1):
        """Get transactions due within specified days"""
        due_threshold = datetime.utcnow() + timedelta(days=days)
        return cls.query.filter(
            cls.status == TransactionStatus.BORROWED,
            cls.due_date <= due_threshold,
            cls.due_date > datetime.utcnow()
        ).all()
    
    @classmethod
    def get_item_history(cls, item_id, limit=None):
        """Get transaction history for an item"""
        query = cls.query.filter_by(item_id=item_id).order_by(cls.requested_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @classmethod
    def get_statistics(cls, start_date=None, end_date=None):
        """Get transaction statistics"""
        query = cls.query
        
        if start_date:
            query = query.filter(cls.requested_at >= start_date)
        if end_date:
            query = query.filter(cls.requested_at <= end_date)
        
        total_transactions = query.count()
        
        # Count by status
        status_counts = {}
        for status in TransactionStatus:
            count = query.filter_by(status=status).count()
            status_counts[status.value] = count
        
        # Overdue count
        overdue_count = cls.query.filter(
            cls.status == TransactionStatus.BORROWED,
            cls.due_date < datetime.utcnow()
        ).count()
        
        return {
            'total_transactions': total_transactions,
            'status_counts': status_counts,
            'overdue_count': overdue_count,
            'approval_rate': (status_counts.get('approved', 0) + status_counts.get('borrowed', 0)) / max(total_transactions, 1) * 100
        }