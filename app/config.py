"""
Configuration settings for D-Block Library Management System
"""
import os
from datetime import timedelta


class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    
    # Security settings
    WTF_CSRF_TIME_LIMIT = None
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Application settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file upload
    LANGUAGES = ['en']
    
    # Notification settings
    NOTIFICATION_RATE_LIMIT = 3  # Max notifications per item per day
    
    # Fine settings
    DEFAULT_FINE_RATE = 5.00  # Default daily fine rate
    MAX_RENEWALS = 4
    DEFAULT_LOAN_DAYS = 7
    
    # Rate limiting settings
    RATELIMIT_STORAGE_URL = "memory://"
    RATELIMIT_DEFAULT = "100 per hour"
    RATELIMIT_ENABLED = True
    
    # Audit logging settings
    AUDIT_LOG_RETENTION_DAYS = 365  # 1 year retention
    AUDIT_LOG_CLEANUP_ENABLED = True
    AUDIT_LOG_MAX_ENTRIES = 1000000  # Maximum entries before forced cleanup
    
    @staticmethod
    def init_app(app):
        # Add security headers
        @app.after_request
        def add_security_headers(response):
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            return response


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.dirname(os.path.dirname(__file__)), 'library.db')
    
    # Enable CSRF in development for proper testing
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_SECURE = False


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Production configuration"""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://user:password@localhost/library_db'
    
    # Enhanced security for production
    FORCE_HTTPS = True
    
    # Production rate limiting with Redis
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    RATELIMIT_DEFAULT = "200 per hour"
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Force HTTPS in production
        @app.before_request
        def force_https():
            from flask import request, redirect
            if not request.is_secure and app.config.get('FORCE_HTTPS'):
                return redirect(request.url.replace('http://', 'https://'))


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}