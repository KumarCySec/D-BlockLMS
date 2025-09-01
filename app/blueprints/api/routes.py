"""
API routes with standardized responses and error handling
"""
from datetime import datetime
from flask import jsonify, request, current_app
from flask_login import current_user
from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden, NotFound, InternalServerError
from app.blueprints.api import bp
from app.utils.auth import login_required_with_status, role_required
from app.models.user import User
from app.models.role import Role
from app.models.department import Department
from app import csrf


class APIResponse:
    """Standardized API response format"""
    
    @staticmethod
    def success(data=None, message="Success", status_code=200):
        """Success response"""
        response = {
            'success': True,
            'message': message,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data
        }
        return jsonify(response), status_code
    
    @staticmethod
    def error(message="An error occurred", status_code=400, error_code=None, details=None):
        """Error response"""
        response = {
            'success': False,
            'message': message,
            'timestamp': datetime.utcnow().isoformat(),
            'error': {
                'code': error_code or status_code,
                'details': details
            }
        }
        return jsonify(response), status_code
    
    @staticmethod
    def validation_error(errors):
        """Validation error response"""
        return APIResponse.error(
            message="Validation failed",
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=errors
        )


# Error handlers
@bp.errorhandler(400)
def bad_request(error):
    """Handle bad request errors"""
    return APIResponse.error("Bad request", 400, "BAD_REQUEST")


@bp.errorhandler(401)
def unauthorized(error):
    """Handle unauthorized errors"""
    return APIResponse.error("Authentication required", 401, "UNAUTHORIZED")


@bp.errorhandler(403)
def forbidden(error):
    """Handle forbidden errors"""
    return APIResponse.error("Access forbidden", 403, "FORBIDDEN")


@bp.errorhandler(404)
def not_found(error):
    """Handle not found errors"""
    return APIResponse.error("Resource not found", 404, "NOT_FOUND")


@bp.errorhandler(500)
def internal_error(error):
    """Handle internal server errors"""
    current_app.logger.error(f"Internal server error: {error}")
    return APIResponse.error("Internal server error", 500, "INTERNAL_ERROR")


# Health and system endpoints
@bp.route('/health')
def health():
    """Health check endpoint"""
    return APIResponse.success({
        'service': 'D-Block Library Management System',
        'version': '1.0.0',
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })


@bp.route('/system/info')
@login_required_with_status
def system_info():
    """System information endpoint"""
    return APIResponse.success({
        'user': {
            'id': current_user.id,
            'name': current_user.name,
            'email': current_user.email,
            'roles': current_user.get_role_names(),
            'permissions': current_user.get_permissions(),
            'department': current_user.department.name if current_user.department else None
        },
        'system': {
            'version': '1.0.0',
            'environment': current_app.config.get('FLASK_ENV', 'production')
        }
    })


# User management endpoints
@bp.route('/users')
@role_required('Admin', 'Incharge')
def get_users():
    """Get users list with filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    status = request.args.get('status')
    department_id = request.args.get('department_id', type=int)
    role_name = request.args.get('role')
    
    query = User.query
    
    # Apply filters
    if status:
        from app.models.user import UserStatus
        try:
            status_enum = UserStatus(status)
            query = query.filter(User.status == status_enum)
        except ValueError:
            return APIResponse.error("Invalid status value", 400)
    
    if department_id:
        query = query.filter(User.department_id == department_id)
    
    if role_name:
        role = Role.get_by_name(role_name)
        if role:
            query = query.filter(User.roles.contains(role))
        else:
            return APIResponse.error("Invalid role name", 400)
    
    # For incharge, limit to their department
    if current_user.has_role('Incharge') and not current_user.has_role('Admin'):
        query = query.filter(User.department_id == current_user.department_id)
    
    # Paginate
    pagination = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    users_data = [user.to_dict() for user in pagination.items]
    
    return APIResponse.success({
        'users': users_data,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    })


@bp.route('/users/<int:user_id>')
@role_required('Admin', 'Incharge')
def get_user(user_id):
    """Get specific user details"""
    user = User.query.get_or_404(user_id)
    
    # Check permissions
    if current_user.has_role('Incharge') and not current_user.has_role('Admin'):
        if user.department_id != current_user.department_id:
            return APIResponse.error("Access forbidden", 403)
    
    return APIResponse.success({'user': user.to_dict(include_sensitive=True)})


@bp.route('/users/<int:user_id>/approve', methods=['POST'])
@role_required('Admin', 'Incharge')
def approve_user(user_id):
    """Approve user registration"""
    user = User.query.get_or_404(user_id)
    
    # Check permissions
    if current_user.has_role('Incharge') and not current_user.has_role('Admin'):
        if user.department_id != current_user.department_id:
            return APIResponse.error("Access forbidden", 403)
    
    if not user.is_pending_approval():
        return APIResponse.error("User is not pending approval", 400)
    
    from app.models.user import UserStatus
    user.status = UserStatus.ACTIVE
    
    try:
        from app import db
        db.session.commit()
        return APIResponse.success(
            {'user': user.to_dict()},
            f"User {user.name} approved successfully"
        )
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error approving user {user_id}: {e}")
        return APIResponse.error("Failed to approve user", 500)


# Department endpoints
@bp.route('/departments')
@login_required_with_status
def get_departments():
    """Get departments list"""
    departments = Department.get_active_departments()
    departments_data = [dept.to_dict(include_stats=True) for dept in departments]
    
    return APIResponse.success({'departments': departments_data})


@bp.route('/departments/<int:dept_id>')
@login_required_with_status
def get_department(dept_id):
    """Get specific department details"""
    department = Department.query.get_or_404(dept_id)
    
    return APIResponse.success({'department': department.to_dict(include_stats=True)})


# Role endpoints
@bp.route('/roles')
@role_required('Admin')
def get_roles():
    """Get roles list"""
    roles = Role.get_all_roles()
    roles_data = [role.to_dict() for role in roles]
    
    return APIResponse.success({'roles': roles_data})