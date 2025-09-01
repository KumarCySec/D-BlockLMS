"""
Audit logging utilities and decorators
"""
from functools import wraps
from flask import request, current_app
from flask_login import current_user
from app.models.audit_log import AuditLog, AuditAction, AuditSeverity


class AuditService:
    """Service class for audit logging operations"""
    
    @staticmethod
    def log_login_success(user):
        """Log successful login"""
        AuditLog.log_action(
            action=AuditAction.LOGIN,
            description=f"User {user.email} logged in successfully",
            target_type='User',
            target_id=user.id,
            target_identifier=user.email,
            severity=AuditSeverity.INFO
        )
    
    @staticmethod
    def log_login_failure(email, reason="Invalid credentials"):
        """Log failed login attempt"""
        AuditLog.log_action(
            action=AuditAction.FAILED_LOGIN,
            description=f"Failed login attempt for {email}: {reason}",
            target_identifier=email,
            severity=AuditSeverity.WARNING
        )
    
    @staticmethod
    def log_logout(user):
        """Log user logout"""
        AuditLog.log_action(
            action=AuditAction.LOGOUT,
            description=f"User {user.email} logged out",
            target_type='User',
            target_id=user.id,
            target_identifier=user.email,
            severity=AuditSeverity.INFO
        )
    
    @staticmethod
    def log_user_registration(user):
        """Log user registration"""
        AuditLog.log_action(
            action=AuditAction.REGISTER,
            description=f"New user registered: {user.email} ({user.name})",
            target_type='User',
            target_id=user.id,
            target_identifier=user.email,
            severity=AuditSeverity.INFO,
            metadata={
                'roll_number': user.roll_number,
                'branch': user.branch,
                'batch': user.batch,
                'department_id': user.department_id
            }
        )
    
    @staticmethod
    def log_user_approval(approved_user, approver):
        """Log user approval"""
        AuditLog.log_action(
            action=AuditAction.USER_APPROVE,
            description=f"User {approved_user.email} approved by {approver.email}",
            target_type='User',
            target_id=approved_user.id,
            target_identifier=approved_user.email,
            severity=AuditSeverity.INFO,
            metadata={
                'approver_id': approver.id,
                'approver_email': approver.email
            }
        )
    
    @staticmethod
    def log_user_update(updated_user, changes):
        """Log user profile updates"""
        AuditLog.log_action(
            action=AuditAction.USER_UPDATE,
            description=f"User {updated_user.email} profile updated",
            target_type='User',
            target_id=updated_user.id,
            target_identifier=updated_user.email,
            severity=AuditSeverity.INFO,
            metadata={'changes': changes}
        )
    
    @staticmethod
    def log_role_assignment(user, role, assigned_by):
        """Log role assignment"""
        AuditLog.log_action(
            action=AuditAction.ROLE_ASSIGN,
            description=f"Role '{role.name}' assigned to {user.email} by {assigned_by.email}",
            target_type='User',
            target_id=user.id,
            target_identifier=user.email,
            severity=AuditSeverity.INFO,
            metadata={
                'role_id': role.id,
                'role_name': role.name,
                'assigned_by_id': assigned_by.id,
                'assigned_by_email': assigned_by.email
            }
        )
    
    @staticmethod
    def log_unauthorized_access(resource, reason="Insufficient permissions"):
        """Log unauthorized access attempts"""
        AuditLog.log_action(
            action=AuditAction.UNAUTHORIZED_ACCESS,
            description=f"Unauthorized access attempt to {resource}: {reason}",
            severity=AuditSeverity.WARNING,
            metadata={
                'resource': resource,
                'reason': reason,
                'user_roles': current_user.get_role_names() if current_user.is_authenticated else []
            }
        )
    
    @staticmethod
    def log_data_export(export_type, record_count):
        """Log data export operations"""
        AuditLog.log_action(
            action=AuditAction.DATA_EXPORT,
            description=f"Data export: {export_type} ({record_count} records)",
            severity=AuditSeverity.INFO,
            metadata={
                'export_type': export_type,
                'record_count': record_count
            }
        )
    
    @staticmethod
    def log_system_config_change(setting_name, old_value, new_value):
        """Log system configuration changes"""
        AuditLog.log_action(
            action=AuditAction.SYSTEM_CONFIG,
            description=f"System configuration changed: {setting_name}",
            severity=AuditSeverity.INFO,
            metadata={
                'setting_name': setting_name,
                'old_value': old_value,
                'new_value': new_value
            }
        )
    
    @staticmethod
    def log_suspicious_activity(description, metadata=None):
        """Log suspicious activity"""
        AuditLog.log_action(
            action=AuditAction.SUSPICIOUS_ACTIVITY,
            description=description,
            severity=AuditSeverity.CRITICAL,
            metadata=metadata
        )


def audit_action(action, description_template=None, target_type=None, 
                severity=AuditSeverity.INFO, include_args=False):
    """Decorator for automatic audit logging of function calls"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Execute the function first
            result = f(*args, **kwargs)
            
            # Prepare audit log data
            description = description_template or f"Function {f.__name__} executed"
            
            # Include function arguments in metadata if requested
            metadata = None
            if include_args:
                metadata = {
                    'function': f.__name__,
                    'args': str(args) if args else None,
                    'kwargs': kwargs if kwargs else None
                }
            
            # Determine target information from result if it's a model instance
            target_id = None
            target_identifier = None
            
            if hasattr(result, 'id'):
                target_id = result.id
            
            if hasattr(result, 'email'):
                target_identifier = result.email
            elif hasattr(result, 'name'):
                target_identifier = result.name
            
            # Create audit log
            AuditLog.log_action(
                action=action,
                description=description,
                target_type=target_type,
                target_id=target_id,
                target_identifier=target_identifier,
                severity=severity,
                metadata=metadata
            )
            
            return result
        return decorated_function
    return decorator


def audit_login_attempts(f):
    """Decorator specifically for login attempt auditing"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        email = request.form.get('email', '').strip().lower()
        
        try:
            result = f(*args, **kwargs)
            
            # If we get here without exception, login was successful
            # The actual success logging should be done in the login function
            # when we have access to the user object
            
            return result
            
        except Exception as e:
            # Log failed login attempt
            AuditService.log_login_failure(email, str(e))
            raise
    
    return decorated_function


def audit_api_access(f):
    """Decorator for auditing API access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Log API access
        endpoint = request.endpoint or f.__name__
        
        try:
            result = f(*args, **kwargs)
            
            # Log successful API access for sensitive endpoints
            if any(sensitive in endpoint for sensitive in ['admin', 'manage', 'approve', 'delete']):
                AuditLog.log_action(
                    action=AuditAction.SYSTEM_CONFIG,  # Generic action for API access
                    description=f"API endpoint accessed: {endpoint}",
                    severity=AuditSeverity.INFO,
                    metadata={
                        'endpoint': endpoint,
                        'method': request.method,
                        'status': 'success'
                    }
                )
            
            return result
            
        except Exception as e:
            # Log failed API access
            AuditLog.log_action(
                action=AuditAction.UNAUTHORIZED_ACCESS,
                description=f"Failed API access: {endpoint} - {str(e)}",
                severity=AuditSeverity.WARNING,
                metadata={
                    'endpoint': endpoint,
                    'method': request.method,
                    'error': str(e)
                }
            )
            raise
    
    return decorated_function


def audit_user_action(action_type, description_template=None):
    """Decorator for auditing user actions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                result = f(*args, **kwargs)
                
                # Generate description
                description = description_template or f"User action: {f.__name__}"
                if callable(description_template):
                    description = description_template(result, *args, **kwargs)
                
                # Log the action
                AuditLog.log_action(
                    action=action_type,
                    description=description,
                    severity=AuditSeverity.INFO,
                    metadata={
                        'function': f.__name__,
                        'success': True
                    }
                )
                
                return result
                
            except Exception as e:
                # Log failed action
                AuditLog.log_action(
                    action=action_type,
                    description=f"Failed {f.__name__}: {str(e)}",
                    severity=AuditSeverity.ERROR,
                    metadata={
                        'function': f.__name__,
                        'success': False,
                        'error': str(e)
                    }
                )
                raise
        
        return decorated_function
    return decorator


def audit_data_change(target_type, get_target_info=None):
    """Decorator for auditing data changes"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                result = f(*args, **kwargs)
                
                # Get target information
                target_id = None
                target_identifier = None
                
                if get_target_info and callable(get_target_info):
                    target_id, target_identifier = get_target_info(result, *args, **kwargs)
                elif hasattr(result, 'id'):
                    target_id = result.id
                    if hasattr(result, 'email'):
                        target_identifier = result.email
                    elif hasattr(result, 'name'):
                        target_identifier = result.name
                
                # Log the data change
                AuditLog.log_action(
                    action=AuditAction.USER_UPDATE,  # Generic data update action
                    description=f"{target_type} modified via {f.__name__}",
                    target_type=target_type,
                    target_id=target_id,
                    target_identifier=target_identifier,
                    severity=AuditSeverity.INFO,
                    metadata={
                        'function': f.__name__,
                        'operation': 'update'
                    }
                )
                
                return result
                
            except Exception as e:
                # Log failed data change
                AuditLog.log_action(
                    action=AuditAction.USER_UPDATE,
                    description=f"Failed to modify {target_type} via {f.__name__}: {str(e)}",
                    target_type=target_type,
                    severity=AuditSeverity.ERROR,
                    metadata={
                        'function': f.__name__,
                        'operation': 'update',
                        'error': str(e)
                    }
                )
                raise
        
        return decorated_function
    return decorator


class AuditContext:
    """Context manager for batch audit operations"""
    
    def __init__(self, operation_name):
        self.operation_name = operation_name
        self.start_time = None
        self.actions = []
    
    def __enter__(self):
        from datetime import datetime
        self.start_time = datetime.utcnow()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        from datetime import datetime
        end_time = datetime.utcnow()
        duration = (end_time - self.start_time).total_seconds()
        
        if exc_type is None:
            # Success
            AuditLog.log_action(
                action=AuditAction.SYSTEM_CONFIG,
                description=f"Batch operation completed: {self.operation_name}",
                severity=AuditSeverity.INFO,
                metadata={
                    'operation': self.operation_name,
                    'duration_seconds': duration,
                    'actions_count': len(self.actions),
                    'actions': self.actions
                }
            )
        else:
            # Error
            AuditLog.log_action(
                action=AuditAction.SYSTEM_CONFIG,
                description=f"Batch operation failed: {self.operation_name}",
                severity=AuditSeverity.ERROR,
                metadata={
                    'operation': self.operation_name,
                    'duration_seconds': duration,
                    'error': str(exc_val),
                    'actions_completed': len(self.actions)
                }
            )
    
    def add_action(self, action_description):
        """Add an action to the batch operation"""
        self.actions.append(action_description)