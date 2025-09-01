"""
Audit logging model for tracking all user actions
"""
from datetime import datetime
from enum import Enum
import json
from flask import request
from flask_login import current_user
from app import db


class AuditAction(Enum):
    """Audit action types"""
    # Authentication actions
    LOGIN = 'login'
    LOGOUT = 'logout'
    REGISTER = 'register'
    PASSWORD_CHANGE = 'password_change'
    
    # User management actions
    USER_CREATE = 'user_create'
    USER_UPDATE = 'user_update'
    USER_DELETE = 'user_delete'
    USER_APPROVE = 'user_approve'
    USER_SUSPEND = 'user_suspend'
    USER_ACTIVATE = 'user_activate'
    
    # Role and permission actions
    ROLE_ASSIGN = 'role_assign'
    ROLE_REMOVE = 'role_remove'
    ROLE_CREATE = 'role_create'
    ROLE_UPDATE = 'role_update'
    
    # Inventory actions
    INVENTORY_CREATE = 'inventory_create'
    INVENTORY_UPDATE = 'inventory_update'
    INVENTORY_DELETE = 'inventory_delete'
    INVENTORY_VIEW = 'inventory_view'
    
    # Transaction actions
    CHECKOUT_REQUEST = 'checkout_request'
    CHECKOUT_APPROVE = 'checkout_approve'
    CHECKOUT_REJECT = 'checkout_reject'
    RETURN_PROCESS = 'return_process'
    RENEWAL_REQUEST = 'renewal_request'
    RENEWAL_APPROVE = 'renewal_approve'
    
    # Waitlist actions
    WAITLIST_JOIN = 'waitlist_join'
    WAITLIST_LEAVE = 'waitlist_leave'
    WAITLIST_CLAIM = 'waitlist_claim'
    
    # Fine actions
    FINE_CALCULATE = 'fine_calculate'
    FINE_WAIVE = 'fine_waive'
    FINE_PAYMENT = 'fine_payment'
    
    # System actions
    SYSTEM_CONFIG = 'system_config'
    DATA_EXPORT = 'data_export'
    DATA_IMPORT = 'data_import'
    
    # Security actions
    FAILED_LOGIN = 'failed_login'
    UNAUTHORIZED_ACCESS = 'unauthorized_access'
    SUSPICIOUS_ACTIVITY = 'suspicious_activity'


class AuditSeverity(Enum):
    """Audit log severity levels"""
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'


class AuditLog(db.Model):
    """Audit log model for comprehensive activity tracking"""
    __tablename__ = 'audit_log'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Action details
    action = db.Column(db.Enum(AuditAction), nullable=False)
    severity = db.Column(db.Enum(AuditSeverity), default=AuditSeverity.INFO, nullable=False)
    description = db.Column(db.Text, nullable=False)
    
    # User information
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user_email = db.Column(db.String(120), nullable=True)  # Store email for deleted users
    user_name = db.Column(db.String(100), nullable=True)   # Store name for deleted users
    
    # Target information (what was acted upon)
    target_type = db.Column(db.String(50), nullable=True)  # e.g., 'User', 'Inventory', 'Transaction'
    target_id = db.Column(db.Integer, nullable=True)
    target_identifier = db.Column(db.String(100), nullable=True)  # e.g., email, roll_number, item_code
    
    # Request information
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 support
    user_agent = db.Column(db.Text, nullable=True)
    request_method = db.Column(db.String(10), nullable=True)
    request_url = db.Column(db.Text, nullable=True)
    
    # Additional data (JSON format)
    extra_data = db.Column(db.Text, nullable=True)  # JSON string for additional context
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = db.relationship('User', backref='audit_logs')
    
    # Indexes for performance
    __table_args__ = (
        db.Index('idx_audit_action', 'action'),
        db.Index('idx_audit_user', 'user_id'),
        db.Index('idx_audit_target', 'target_type', 'target_id'),
        db.Index('idx_audit_created', 'created_at'),
        db.Index('idx_audit_severity', 'severity'),
        db.Index('idx_audit_ip', 'ip_address'),
    )
    
    def __repr__(self):
        return f'<AuditLog {self.action.value} by {self.user_email or "System"}>'
    
    def to_dict(self):
        """Convert audit log to dictionary"""
        return {
            'id': self.id,
            'action': self.action.value,
            'severity': self.severity.value,
            'description': self.description,
            'user': {
                'id': self.user_id,
                'email': self.user_email,
                'name': self.user_name
            },
            'target': {
                'type': self.target_type,
                'id': self.target_id,
                'identifier': self.target_identifier
            },
            'request': {
                'ip_address': self.ip_address,
                'user_agent': self.user_agent,
                'method': self.request_method,
                'url': self.request_url
            },
            'metadata': json.loads(self.extra_data) if self.extra_data else None,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def log_action(cls, action, description, target_type=None, target_id=None, 
                   target_identifier=None, severity=AuditSeverity.INFO, metadata=None):
        """Create an audit log entry"""
        
        # Get current user information
        user_id = None
        user_email = None
        user_name = None
        
        if current_user and current_user.is_authenticated:
            user_id = current_user.id
            user_email = current_user.email
            user_name = current_user.name
        
        # Get request information
        ip_address = None
        user_agent = None
        request_method = None
        request_url = None
        
        if request:
            ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            user_agent = request.headers.get('User-Agent')
            request_method = request.method
            request_url = request.url
        
        # Create audit log entry
        audit_log = cls(
            action=action,
            severity=severity,
            description=description,
            user_id=user_id,
            user_email=user_email,
            user_name=user_name,
            target_type=target_type,
            target_id=target_id,
            target_identifier=target_identifier,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_url=request_url,
            extra_data=json.dumps(metadata) if metadata else None
        )
        
        db.session.add(audit_log)
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            # Log to application logger as fallback
            from flask import current_app
            current_app.logger.error(f"Failed to create audit log: {e}")
        
        return audit_log
    
    @classmethod
    def get_user_activity(cls, user_id, limit=50):
        """Get recent activity for a specific user"""
        return cls.query.filter_by(user_id=user_id)\
                      .order_by(cls.created_at.desc())\
                      .limit(limit).all()
    
    @classmethod
    def get_security_events(cls, hours=24):
        """Get security-related events from the last N hours"""
        from datetime import timedelta
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        security_actions = [
            AuditAction.FAILED_LOGIN,
            AuditAction.UNAUTHORIZED_ACCESS,
            AuditAction.SUSPICIOUS_ACTIVITY,
            AuditAction.USER_SUSPEND,
            AuditAction.PASSWORD_CHANGE
        ]
        
        return cls.query.filter(
            cls.action.in_(security_actions),
            cls.created_at >= cutoff_time
        ).order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_failed_logins(cls, ip_address=None, hours=1):
        """Get failed login attempts"""
        from datetime import timedelta
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        query = cls.query.filter(
            cls.action == AuditAction.FAILED_LOGIN,
            cls.created_at >= cutoff_time
        )
        
        if ip_address:
            query = query.filter(cls.ip_address == ip_address)
        
        return query.count()
    
    @classmethod
    def cleanup_old_logs(cls, days=90):
        """Clean up audit logs older than specified days"""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        deleted_count = cls.query.filter(cls.created_at < cutoff_date).delete()
        db.session.commit()
        
        return deleted_count