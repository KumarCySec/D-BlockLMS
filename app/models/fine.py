"""
Fine calculation and tracking models
"""
from datetime import datetime, date
from enum import Enum
from decimal import Decimal
from app import db
from sqlalchemy import func


class FineRecord(db.Model):
    """Immutable fine tracking record for audit trail"""
    __tablename__ = 'fine_record'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_item.id'), nullable=False)
    
    # Fine calculation details
    fine_date = db.Column(db.Date, nullable=False, default=date.today)
    days_overdue = db.Column(db.Integer, nullable=False)
    daily_rate = db.Column(db.Numeric(10, 2), nullable=False)
    fine_amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Waiver information
    is_waived = db.Column(db.Boolean, default=False, nullable=False)
    waived_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    waived_reason = db.Column(db.Text, nullable=True)
    waived_at = db.Column(db.DateTime, nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    transaction = db.relationship('Transaction', backref='fine_records')
    user = db.relationship('User', foreign_keys=[user_id], backref='fine_records')
    item = db.relationship('InventoryItem', backref='fine_records')
    waiver = db.relationship('User', foreign_keys=[waived_by])
    
    # Indexes for performance
    __table_args__ = (
        db.Index('idx_fine_record_date', 'fine_date'),
        db.Index('idx_fine_record_user', 'user_id'),
        db.Index('idx_fine_record_transaction', 'transaction_id'),
        db.Index('idx_fine_record_waived', 'is_waived'),
        db.Index('idx_fine_record_created', 'created_at'),
    )
    
    def __repr__(self):
        return f'<FineRecord {self.id} - ₹{self.fine_amount} for transaction {self.transaction_id}>'
    
    def waive_fine(self, waiver_user_id, reason=None):
        """Waive this fine record"""
        if self.is_waived:
            raise ValueError("Fine is already waived")
        
        self.is_waived = True
        self.waived_by = waiver_user_id
        self.waived_reason = reason
        self.waived_at = datetime.utcnow()
        
        # Log the waiver
        from app.models.audit_log import AuditLog, AuditAction
        AuditLog.log_action(
            action=AuditAction.FINE_WAIVE,
            description=f"Fine waived for transaction {self.transaction.transaction_id}",
            target_type='FineRecord',
            target_id=self.id,
            target_identifier=f"fine-{self.id}",
            metadata={
                'transaction_id': self.transaction.transaction_id,
                'fine_amount': str(self.fine_amount),
                'reason': reason,
                'waiver_user_id': waiver_user_id,
                'user_id': self.user_id
            }
        )
        
        return True
    
    def to_dict(self, include_user=False, include_item=False, include_transaction=False):
        """Convert fine record to dictionary"""
        data = {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'user_id': self.user_id,
            'item_id': self.item_id,
            'fine_date': self.fine_date.isoformat(),
            'days_overdue': self.days_overdue,
            'daily_rate': str(self.daily_rate),
            'fine_amount': str(self.fine_amount),
            'is_waived': self.is_waived,
            'waived_by': self.waived_by,
            'waived_reason': self.waived_reason,
            'waived_at': self.waived_at.isoformat() if self.waived_at else None,
            'created_at': self.created_at.isoformat()
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
                'item_type': self.item.item_type.value
            }
        
        if include_transaction and self.transaction:
            data['transaction'] = {
                'id': self.transaction.id,
                'transaction_id': self.transaction.transaction_id,
                'status': self.transaction.status.value,
                'due_date': self.transaction.due_date.isoformat() if self.transaction.due_date else None
            }
        
        return data
    
    @classmethod
    def create_fine_record(cls, transaction_id, user_id, item_id, days_overdue, daily_rate):
        """Create a new fine record"""
        fine_amount = days_overdue * daily_rate
        
        fine_record = cls(
            transaction_id=transaction_id,
            user_id=user_id,
            item_id=item_id,
            days_overdue=days_overdue,
            daily_rate=daily_rate,
            fine_amount=fine_amount
        )
        
        db.session.add(fine_record)
        
        # Log fine creation
        from app.models.audit_log import AuditLog, AuditAction
        AuditLog.log_action(
            action=AuditAction.FINE_CALCULATE,
            description=f"Fine calculated: ₹{fine_amount} for {days_overdue} days overdue",
            target_type='FineRecord',
            target_id=fine_record.id,
            target_identifier=f"fine-{fine_record.id}",
            metadata={
                'transaction_id': transaction_id,
                'user_id': user_id,
                'item_id': item_id,
                'days_overdue': days_overdue,
                'daily_rate': str(daily_rate),
                'fine_amount': str(fine_amount)
            }
        )
        
        return fine_record
    
    @classmethod
    def get_user_fines(cls, user_id, include_waived=False):
        """Get all fine records for a user"""
        query = cls.query.filter_by(user_id=user_id)
        
        if not include_waived:
            query = query.filter_by(is_waived=False)
        
        return query.order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_transaction_fines(cls, transaction_id):
        """Get all fine records for a transaction"""
        return cls.query.filter_by(transaction_id=transaction_id).order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_pending_fines(cls, department_id=None):
        """Get all pending (non-waived) fines"""
        query = cls.query.filter_by(is_waived=False)
        
        if department_id:
            query = query.join(cls.user).filter_by(department_id=department_id)
        
        return query.order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_fine_statistics(cls, start_date=None, end_date=None, department_id=None):
        """Get fine statistics"""
        query = cls.query
        
        if start_date:
            query = query.filter(cls.fine_date >= start_date)
        if end_date:
            query = query.filter(cls.fine_date <= end_date)
        if department_id:
            query = query.join(cls.user).filter_by(department_id=department_id)
        
        total_fines = query.count()
        total_amount = query.with_entities(func.sum(cls.fine_amount)).scalar() or Decimal('0.00')
        waived_fines = query.filter_by(is_waived=True).count()
        waived_amount = query.filter_by(is_waived=True).with_entities(func.sum(cls.fine_amount)).scalar() or Decimal('0.00')
        
        return {
            'total_fines': total_fines,
            'total_amount': float(total_amount),
            'waived_fines': waived_fines,
            'waived_amount': float(waived_amount),
            'pending_fines': total_fines - waived_fines,
            'pending_amount': float(total_amount - waived_amount)
        }


class FineConfiguration(db.Model):
    """Configurable fine rules for different item types"""
    __tablename__ = 'fine_configuration'
    
    id = db.Column(db.Integer, primary_key=True)
    item_type = db.Column(db.Enum('book', 'laptop', 'kit', name='item_type_enum'), nullable=False, unique=True)
    daily_rate = db.Column(db.Numeric(10, 2), nullable=False)
    grace_period_days = db.Column(db.Integer, default=0, nullable=False)
    max_fine_amount = db.Column(db.Numeric(10, 2), nullable=True)
    escalation_days = db.Column(db.Integer, default=7, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Relationships
    updater = db.relationship('User')
    
    # Indexes
    __table_args__ = (
        db.Index('idx_fine_config_type', 'item_type'),
        db.Index('idx_fine_config_active', 'is_active'),
    )
    
    def __repr__(self):
        return f'<FineConfiguration {self.item_type} - ₹{self.daily_rate}/day>'
    
    def calculate_fine(self, days_overdue):
        """Calculate fine for given days overdue"""
        if days_overdue <= self.grace_period_days:
            return Decimal('0.00')
        
        effective_days = days_overdue - self.grace_period_days
        calculated_fine = effective_days * self.daily_rate
        
        if self.max_fine_amount:
            return min(calculated_fine, self.max_fine_amount)
        
        return calculated_fine
    
    def to_dict(self):
        """Convert fine configuration to dictionary"""
        return {
            'id': self.id,
            'item_type': self.item_type,
            'daily_rate': str(self.daily_rate),
            'grace_period_days': self.grace_period_days,
            'max_fine_amount': str(self.max_fine_amount) if self.max_fine_amount else None,
            'escalation_days': self.escalation_days,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'updated_by': self.updated_by
        }
    
    @classmethod
    def get_by_item_type(cls, item_type):
        """Get fine configuration for item type"""
        return cls.query.filter_by(item_type=item_type, is_active=True).first()
    
    @classmethod
    def get_all_active(cls):
        """Get all active fine configurations"""
        return cls.query.filter_by(is_active=True).order_by(cls.item_type).all()
    
    @classmethod
    def update_configuration(cls, item_type, daily_rate, grace_period_days=0, 
                           max_fine_amount=None, escalation_days=7, updated_by=None):
        """Update or create fine configuration"""
        config = cls.get_by_item_type(item_type)
        
        if not config:
            config = cls(item_type=item_type)
            db.session.add(config)
        
        config.daily_rate = daily_rate
        config.grace_period_days = grace_period_days
        config.max_fine_amount = max_fine_amount
        config.escalation_days = escalation_days
        config.updated_by = updated_by
        config.updated_at = datetime.utcnow()
        
        # Log configuration change
        from app.models.audit_log import AuditLog, AuditAction
        AuditLog.log_action(
            action=AuditAction.SYSTEM_CONFIG,
            description=f"Fine configuration updated for {item_type}",
            target_type='FineConfiguration',
            target_id=config.id,
            target_identifier=f"fine-config-{item_type}",
            metadata={
                'item_type': item_type,
                'daily_rate': str(daily_rate),
                'grace_period_days': grace_period_days,
                'max_fine_amount': str(max_fine_amount) if max_fine_amount else None,
                'escalation_days': escalation_days,
                'updated_by': updated_by
            }
        )
        
        return config
    
    @classmethod
    def create_default_configurations(cls):
        """Create default fine configurations"""
        default_configs = [
            {
                'item_type': 'book',
                'daily_rate': Decimal('1.00'),
                'grace_period_days': 1,
                'max_fine_amount': Decimal('50.00'),
                'escalation_days': 7
            },
            {
                'item_type': 'laptop',
                'daily_rate': Decimal('10.00'),
                'grace_period_days': 0,
                'max_fine_amount': Decimal('500.00'),
                'escalation_days': 3
            },
            {
                'item_type': 'kit',
                'daily_rate': Decimal('5.00'),
                'grace_period_days': 1,
                'max_fine_amount': Decimal('200.00'),
                'escalation_days': 5
            }
        ]
        
        created_configs = []
        for config_data in default_configs:
            existing_config = cls.get_by_item_type(config_data['item_type'])
            if not existing_config:
                config = cls(**config_data)
                db.session.add(config)
                created_configs.append(config)
        
        if created_configs:
            db.session.commit()
        
        return created_configs


class FineService:
    """Service class for fine calculation and management"""
    
    @staticmethod
    def calculate_transaction_fine(transaction):
        """Calculate fine for a transaction"""
        from app.models.transaction import TransactionStatus
        
        if transaction.status != TransactionStatus.BORROWED:
            return Decimal('0.00')
        
        if not transaction.due_date:
            return Decimal('0.00')
        
        # Calculate days overdue
        days_overdue = (datetime.utcnow() - transaction.due_date).days
        
        if days_overdue <= 0:
            return Decimal('0.00')
        
        # Get fine configuration for item type
        config = FineConfiguration.get_by_item_type(transaction.item.item_type.value)
        
        if not config:
            # Default fine rate if no configuration
            return days_overdue * Decimal('1.00')
        
        return config.calculate_fine(days_overdue)
    
    @staticmethod
    def create_daily_fine_records():
        """Create fine records for all overdue transactions (daily job)"""
        from app.models.transaction import Transaction, TransactionStatus
        
        # Get all overdue transactions
        overdue_transactions = Transaction.query.filter(
            Transaction.status == TransactionStatus.BORROWED,
            Transaction.due_date < datetime.utcnow()
        ).all()
        
        created_records = []
        
        for transaction in overdue_transactions:
            days_overdue = (datetime.utcnow() - transaction.due_date).days
            
            if days_overdue <= 0:
                continue
            
            # Check if fine record already exists for today
            existing_record = FineRecord.query.filter_by(
                transaction_id=transaction.id,
                fine_date=date.today()
            ).first()
            
            if existing_record:
                continue
            
            # Get fine configuration
            config = FineConfiguration.get_by_item_type(transaction.item.item_type.value)
            daily_rate = config.daily_rate if config else Decimal('1.00')
            
            # Create fine record
            fine_record = FineRecord.create_fine_record(
                transaction_id=transaction.id,
                user_id=transaction.user_id,
                item_id=transaction.item_id,
                days_overdue=days_overdue,
                daily_rate=daily_rate
            )
            
            created_records.append(fine_record)
        
        if created_records:
            db.session.commit()
        
        return created_records
    
    @staticmethod
    def get_user_fine_summary(user_id):
        """Get comprehensive fine summary for a user"""
        fine_records = FineRecord.get_user_fines(user_id, include_waived=True)
        
        total_fines = len(fine_records)
        total_amount = sum(record.fine_amount for record in fine_records)
        pending_amount = sum(record.fine_amount for record in fine_records if not record.is_waived)
        waived_amount = sum(record.fine_amount for record in fine_records if record.is_waived)
        
        return {
            'user_id': user_id,
            'total_fines': total_fines,
            'total_amount': float(total_amount),
            'pending_amount': float(pending_amount),
            'waived_amount': float(waived_amount),
            'fine_records': [record.to_dict(include_item=True, include_transaction=True) for record in fine_records]
        }
    
    @staticmethod
    def get_department_fine_summary(department_id):
        """Get fine summary for a department"""
        from app.models.user import User
        
        # Get all users in department
        users = User.query.filter_by(department_id=department_id).all()
        user_ids = [user.id for user in users]
        
        if not user_ids:
            return {
                'department_id': department_id,
                'total_users': 0,
                'users_with_fines': 0,
                'total_fines': 0,
                'total_amount': 0.0,
                'pending_amount': 0.0,
                'waived_amount': 0.0
            }
        
        # Get all fine records for department users
        fine_records = FineRecord.query.filter(FineRecord.user_id.in_(user_ids)).all()
        
        users_with_fines = len(set(record.user_id for record in fine_records))
        total_fines = len(fine_records)
        total_amount = sum(record.fine_amount for record in fine_records)
        pending_amount = sum(record.fine_amount for record in fine_records if not record.is_waived)
        waived_amount = sum(record.fine_amount for record in fine_records if record.is_waived)
        
        return {
            'department_id': department_id,
            'total_users': len(users),
            'users_with_fines': users_with_fines,
            'total_fines': total_fines,
            'total_amount': float(total_amount),
            'pending_amount': float(pending_amount),
            'waived_amount': float(waived_amount)
        }