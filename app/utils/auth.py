"""
Authentication utilities and decorators
"""
from functools import wraps
from flask import abort, redirect, url_for, flash
from flask_login import current_user


def login_required_with_status(f):
    """Decorator that requires login and active status"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('auth.login'))
        
        if not current_user.is_active_user():
            flash('Your account is not active. Please contact an administrator.', 'warning')
            return redirect(url_for('main.index'))
        
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """Decorator that requires specific roles"""
    def decorator(f):
        @wraps(f)
        @login_required_with_status
        def decorated_function(*args, **kwargs):
            if not any(current_user.has_role(role) for role in roles):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def permission_required(permission):
    """Decorator that requires specific permission"""
    def decorator(f):
        @wraps(f)
        @login_required_with_status
        def decorated_function(*args, **kwargs):
            user_permissions = current_user.get_permissions()
            if permission not in user_permissions:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """Decorator that requires admin role"""
    return role_required('Admin')(f)


def incharge_or_admin_required(f):
    """Decorator that requires incharge or admin role"""
    return role_required('Admin', 'Incharge')(f)


def volunteer_or_higher_required(f):
    """Decorator that requires volunteer, incharge, or admin role"""
    return role_required('Admin', 'Incharge', 'Volunteer')(f)


def can_approve_users(user):
    """Check if user can approve other users"""
    return user.has_role('Admin') or user.has_role('Incharge')


def can_manage_department(user, department_id):
    """Check if user can manage a specific department"""
    if user.has_role('Admin'):
        return True
    
    if user.has_role('Incharge') and user.department_id == department_id:
        return True
    
    return False


def can_approve_transaction(user, transaction_department_id=None):
    """Check if user can approve transactions"""
    if user.has_role('Admin'):
        return True
    
    if user.has_role('Incharge'):
        # Incharge can approve transactions in their department
        if transaction_department_id is None or user.department_id == transaction_department_id:
            return True
    
    if user.has_role('Volunteer'):
        # Volunteers can approve transactions in their department
        if transaction_department_id is None or user.department_id == transaction_department_id:
            return True
    
    return False


def get_user_context():
    """Get user context for templates"""
    if not current_user.is_authenticated:
        return {}
    
    return {
        'is_admin': current_user.has_role('Admin'),
        'is_incharge': current_user.has_role('Incharge'),
        'is_volunteer': current_user.has_role('Volunteer'),
        'is_student': current_user.has_role('Student'),
        'can_approve_users': can_approve_users(current_user),
        'can_manage_inventory': current_user.can_manage_inventory(),
        'can_approve_transactions': current_user.can_approve_transactions(),
        'user_permissions': current_user.get_permissions(),
        'user_roles': current_user.get_role_names()
    }