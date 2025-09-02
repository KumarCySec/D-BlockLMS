"""
D-Block Library Management System
Flask Application Factory
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
import os

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

# Rate limiting will be added when Flask-Limiter is available
limiter = None
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(key_func=get_remote_address)
except ImportError:
    pass


def create_app(config_name=None):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app.config.from_object(f'app.config.{config_name.title()}Config')
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Initialize rate limiter if available
    if limiter:
        limiter.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))
    
    # Register blueprints
    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.main import bp as main_bp
    from app.blueprints.api import bp as api_bp
    from app.blueprints.inventory import bp as inventory_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(inventory_bp)
    
    # Import models to ensure they're registered
    from app.models import user, role, department
    
    # Register error handlers
    register_error_handlers(app)
    
    # Add template context processors
    @app.context_processor
    def inject_user_context():
        from app.utils.auth import get_user_context
        return get_user_context()
    
    # Initialize scheduled tasks (development only)
    if app.config.get('FLASK_ENV') == 'development':
        try:
            from app.utils.scheduler import setup_scheduled_tasks
            setup_scheduled_tasks(app)
        except Exception as e:
            app.logger.warning(f"Could not initialize scheduled tasks: {e}")
    
    return app


def register_error_handlers(app):
    """Register application error handlers"""
    
    @app.errorhandler(400)
    def bad_request(error):
        from flask import render_template, request, jsonify
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'message': 'Bad request',
                'error': {'code': 400, 'description': str(error)}
            }), 400
        return render_template('errors/400.html'), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        from flask import render_template, request, jsonify
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'message': 'Authentication required',
                'error': {'code': 401}
            }), 401
        return render_template('errors/401.html'), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        from flask import render_template, request, jsonify
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'message': 'Access forbidden',
                'error': {'code': 403}
            }), 403
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found(error):
        from flask import render_template, request, jsonify
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'message': 'Resource not found',
                'error': {'code': 404}
            }), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(422)
    def validation_error(error):
        from flask import request, jsonify
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'message': 'Validation failed',
                'error': {'code': 422, 'details': getattr(error, 'data', {})}
            }), 422
        return render_template('errors/422.html'), 422
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        from flask import request, jsonify
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'message': 'Rate limit exceeded',
                'error': {'code': 429, 'retry_after': getattr(error, 'retry_after', None)}
            }), 429
        return render_template('errors/429.html'), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template, request, jsonify
        from app import db
        db.session.rollback()
        
        # Log the error
        app.logger.error(f'Internal server error: {error}', exc_info=True)
        
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'message': 'Internal server error',
                'error': {'code': 500}
            }), 500
        return render_template('errors/500.html'), 500
    
    # Handle database errors
    @app.errorhandler(Exception)
    def handle_database_errors(error):
        from flask import request, jsonify
        from sqlalchemy.exc import IntegrityError, OperationalError
        
        if isinstance(error, IntegrityError):
            db.session.rollback()
            if request.path.startswith('/api/'):
                return jsonify({
                    'success': False,
                    'message': 'Data integrity error',
                    'error': {'code': 409, 'type': 'integrity_error'}
                }), 409
        
        if isinstance(error, OperationalError):
            db.session.rollback()
            if request.path.startswith('/api/'):
                return jsonify({
                    'success': False,
                    'message': 'Database operation failed',
                    'error': {'code': 503, 'type': 'operational_error'}
                }), 503
        
        # Re-raise if not handled
        raise error