from flask import Flask, flash, redirect, url_for, current_app
from flask_socketio import SocketIO
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_redis import FlaskRedis
import os
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
from config import Config, DevelopmentConfig, TestingConfig, ProductionConfig

# Import security modules
from .security_config import create_security_manager
from .middleware import SecurityMiddleware, RequestValidator, CSRFProtection
from .rate_limiting import setup_rate_limiting
from .cors_config import setup_secure_cors
from .security_headers import setup_security_headers
from .audit_logger import setup_audit_logging, AuditEventType, AuditSeverity, audit_login, audit_data_access
from .secure_code_executor import SecureCodeExecutor
from .secure_upload import SecureFileUpload

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
redis_client = FlaskRedis()
login_manager = LoginManager()

def create_secure_app(config_class=Config):
    """Create Flask app with comprehensive security"""
    
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize core extensions first
    db.init_app(app)
    migrate.init_app(app, db)
    redis_client.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Initialize security manager - this sets up all security components
    security_manager = create_security_manager(app)
    
    # Configure SocketIO with security considerations
    socketio_config = _get_secure_socketio_config(app.config.get('ENV', 'development'))
    socketio = SocketIO(**socketio_config)
    socketio.init_app(app)
    
    # Store SocketIO in app for access
    app.socketio = socketio
    
    # GitHub OAuth config validation
    if not app.config.get('GITHUB_CLIENT_ID') or not app.config.get('GITHUB_CLIENT_SECRET'):
        app.logger.warning("GitHub OAuth credentials not found in .env file")
    
    # Environment-specific configuration
    _configure_environment(app, config_class)
    
    # Setup enhanced logging with security events
    _setup_enhanced_logging(app)
    
    # Register security-enhanced blueprints
    _register_secure_blueprints(app)
    
    # Setup user loader with audit logging
    _setup_secure_user_loader(app)
    
    # Initialize Celery with security context
    _setup_secure_celery(app)
    
    # Add security utility functions to Jinja2
    _setup_secure_jinja_env(app)
    
    # Import models to ensure they're registered
    from .models import User, OAuth, Score, Problem, Submission, GameModeDetails, TriviaQuestion, DebugChallenge
    
    # Import enhanced socket events with security
    from . import secure_socket
    
    # Add security CLI commands
    _register_security_commands(app)
    
    # Final security validation
    _validate_security_setup(app)
    
    return app

def _get_secure_socketio_config(env: str) -> dict:
    """Get secure SocketIO configuration based on environment"""
    
    if env == 'production':
        return {
            'cors_allowed_origins': [],  # Will be set by CORS middleware
            'ping_timeout': 60,
            'ping_interval': 25,
            'max_http_buffer_size': 1024 * 1024,  # 1MB limit
            'logger': False,
            'engineio_logger': False,
            'async_mode': 'threading',
            'manage_session': False  # Let Flask-Login handle sessions
        }
    else:
        return {
            'cors_allowed_origins': ['http://localhost:3000', 'http://127.0.0.1:3000'],
            'ping_timeout': 60,
            'ping_interval': 25,
            'max_http_buffer_size': 5 * 1024 * 1024,  # 5MB for development
            'logger': True,
            'engineio_logger': True,
            'async_mode': 'threading'
        }

def _configure_environment(app: Flask, config_class):
    """Configure environment-specific settings"""
    
    if isinstance(config_class, ProductionConfig):
        # Production-specific security settings
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
        app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
        
        # Configure production logging
        if not app.logger.handlers:
            handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3)
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
            )
            handler.setFormatter(formatter)
            app.logger.addHandler(handler)
    
    elif isinstance(config_class, DevelopmentConfig):
        # Development-specific settings
        app.config['SESSION_COOKIE_SECURE'] = False  # Allow HTTP in dev
        app.config['WTF_CSRF_TIME_LIMIT'] = None  # Disable CSRF timeout in dev
        
    elif isinstance(config_class, TestingConfig):
        # Testing-specific settings
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for tests
        app.config['LOGIN_DISABLED'] = True  # Disable login requirement for tests

def _setup_enhanced_logging(app: Flask):
    """Setup enhanced logging with security event correlation"""
    
    # Custom log formatter that includes security context
    class SecurityLogFormatter(logging.Formatter):
        def format(self, record):
            # Add security context to log records
            if hasattr(app, 'security') and hasattr(app.security, 'get_component'):
                audit_logger = app.security.get_component('audit')
                if audit_logger and hasattr(record, 'request_id'):
                    record.request_id = getattr(record, 'request_id', 'unknown')
            
            return super().format(record)
    
    # Apply security formatter to existing handlers
    for handler in app.logger.handlers:
        if not isinstance(handler.formatter, SecurityLogFormatter):
            handler.setFormatter(SecurityLogFormatter(
                '[%(asctime)s] %(levelname)s [%(request_id)s] %(message)s'
            ))

def _register_secure_blueprints(app: Flask):
    """Register blueprints with security enhancements"""
    
    # Import blueprints
    from .auth import auth
    from .main import main
    from .oauth import make_github_blueprint
    
    # Register main blueprint with security decorators
    app.register_blueprint(main)
    
    # Register auth blueprint with audit logging
    app.register_blueprint(auth)
    
    # Enhanced GitHub OAuth blueprint
    if app.config.get('GITHUB_CLIENT_ID') and app.config.get('GITHUB_CLIENT_SECRET'):
        github_bp = make_github_blueprint(app)
        app.register_blueprint(github_bp, url_prefix="/login")
    
    # Register security management blueprint
    from .security_admin import create_security_admin_blueprint
    security_admin_bp = create_security_admin_blueprint(app)
    app.register_blueprint(security_admin_bp, url_prefix="/admin/security")

def _setup_secure_user_loader(app: Flask):
    """Setup user loader with security audit logging"""
    
    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        user = User.query.get(int(user_id))
        
        # Log user access for audit
        if app.extensions.get('audit_logger'):
            audit_logger = app.extensions['audit_logger']
            audit_logger.log_event(
                event_type=AuditEventType.DATA_ACCESS,
                severity=AuditSeverity.LOW,
                success=user is not None,
                message=f"User loader accessed for user_id: {user_id}",
                details={'user_found': user is not None},
                user_id=str(user_id) if user else None
            )
        
        return user
    
    @login_manager.unauthorized_handler
    def unauthorized():
        # Log unauthorized access attempts
        if app.extensions.get('audit_logger'):
            audit_logger = app.extensions['audit_logger']
            audit_logger.log_event(
                event_type=AuditEventType.ACCESS_DENIED,
                severity=AuditSeverity.MEDIUM,
                success=False,
                message="Unauthorized access attempt",
                details={'endpoint': request.endpoint if 'request' in globals() else 'unknown'}
            )
        
        flash('You must be logged in to access this page.', 'warning')
        return redirect(url_for('auth.login'))

def _setup_secure_celery(app: Flask):
    """Setup Celery with security context"""
    
    try:
        from .tasks import celery_app
        
        # Update Celery config with security considerations
        celery_config = {
            'task_serializer': 'json',
            'accept_content': ['json'],
            'result_serializer': 'json',
            'timezone': 'UTC',
            'enable_utc': True,
            'task_reject_on_worker_lost': True,
            'task_acks_late': True,
            'worker_prefetch_multiplier': 1,
            'task_time_limit': 300,  # 5 minutes max
            'task_soft_time_limit': 240,  # 4 minutes soft limit
        }
        
        celery_app.conf.update(celery_config)
        celery_app.conf.update(app.config)
        celery_app.app = app
        
    except ImportError:
        app.logger.warning("Celery not available - background tasks disabled")

def _setup_secure_jinja_env(app: Flask):
    """Setup Jinja2 environment with security utilities"""
    
    # Add security utilities to Jinja2 globals
    app.jinja_env.globals.update({
        'enumerate': enumerate,
        'get_security_status': lambda: app.security.get_component('audit') is not None if hasattr(app, 'security') else False,
        'get_csrf_token': lambda: 'csrf_token_placeholder',  # Replace with actual CSRF token function
    })
    
    # Add security filters
    @app.template_filter('sanitize_html')
    def sanitize_html_filter(text):
        from .security import SecurityValidator
        return SecurityValidator.sanitize_html(text)
    
    @app.template_filter('truncate_safe')
    def truncate_safe_filter(text, length=100):
        from .security import SecurityValidator
        sanitized = SecurityValidator.sanitize_text(text, length)
        return sanitized[:length] + '...' if len(sanitized) > length else sanitized

def _register_security_commands(app: Flask):
    """Register additional security CLI commands"""
    
    @app.cli.command('init-security')
    def init_security():
        """Initialize security configuration"""
        click.echo("Initializing security configuration...")
        
        if hasattr(app, 'security'):
            status = app.security._get_security_status()
            for component, info in status.items():
                status_icon = "✓" if info['enabled'] else "✗"
                click.echo(f"{status_icon} {component}: {info['status']}")
        
        click.echo("Security initialization complete!")
    
    @app.cli.command('security-audit')
    def security_audit():
        """Run security audit"""
        click.echo("Running security audit...")
        
        if hasattr(app, 'security'):
            tests = app.security._run_security_tests()
            for test, result in tests.items():
                status_icon = "✓" if result['passed'] else "✗"
                click.echo(f"{status_icon} {test}: {result['message']}")
        
        click.echo("Security audit complete!")

def _validate_security_setup(app: Flask):
    """Validate that all security components are properly configured"""
    
    validation_errors = []
    
    # Check security manager
    if not hasattr(app, 'security'):
        validation_errors.append("Security manager not initialized")
    
    # Check essential security components
    if hasattr(app, 'security'):
        required_components = ['audit', 'limiter', 'headers']
        for component in required_components:
            if not app.security.get_component(component):
                validation_errors.append(f"Required security component missing: {component}")
    
    # Check configuration
    env = app.config.get('ENV', 'development')
    if env == 'production':
        if not app.config.get('SECRET_KEY'):
            validation_errors.append("SECRET_KEY not set for production")
        
        if not app.config.get('SESSION_COOKIE_SECURE', False):
            validation_errors.append("SESSION_COOKIE_SECURE should be True in production")
    
    # Log validation results
    if validation_errors:
        app.logger.error(f"Security validation failed: {validation_errors}")
        if env == 'production':
            raise RuntimeError(f"Security validation failed: {validation_errors}")
    else:
        app.logger.info("Security validation passed")

# Legacy compatibility function
def create_app(config_class=Config):
    """Legacy compatibility wrapper for create_secure_app"""
    app.logger.warning("Using legacy create_app - consider migrating to create_secure_app")
    return create_secure_app(config_class)

# Import click for CLI commands
try:
    import click
except ImportError:
    click = None
    
    # Provide dummy click functions if not available
    class DummyClick:
        @staticmethod
        def echo(message):
            print(message)
        
        @staticmethod
        def command(name):
            def decorator(f):
                return f
            return decorator
    
    click = DummyClick()