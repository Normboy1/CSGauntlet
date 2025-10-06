"""
Enhanced Flask application with proper game functionality and security
This replaces the old app.py with a more robust implementation
"""

from flask import Flask
from flask_socketio import SocketIO
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_redis import FlaskRedis
import os
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
redis_client = FlaskRedis()
socketio = SocketIO()
login_manager = LoginManager()

def create_enhanced_app(config_class=None):
    """Create enhanced Flask application with game functionality and security"""
    
    app = Flask(__name__)
    
    # Load configuration
    if config_class:
        app.config.from_object(config_class)
    else:
        from config import Config
        app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    redis_client.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Configure SocketIO
    socketio_config = {
        'cors_allowed_origins': _get_cors_origins(app.config.get('ENV', 'development')),
        'ping_timeout': 60,
        'ping_interval': 25,
        'async_mode': 'threading',
        'logger': app.config.get('ENV') == 'development',
        'engineio_logger': app.config.get('ENV') == 'development'
    }
    
    socketio.init_app(app, **socketio_config)
    
    # Setup logging
    _setup_logging(app)
    
    # Import models to ensure they're registered
    from .models import User, OAuth, Score, Problem, Submission, GameModeDetails, TriviaQuestion, DebugChallenge
    
    # Register blueprints
    _register_blueprints(app)
    
    # Setup user loader
    _setup_user_loader(app)
    
    # Import and setup socket handlers
    from . import game_socket_handlers
    
    # Setup periodic tasks
    _setup_periodic_tasks(app)
    
    # Add utility functions to Jinja2
    _setup_jinja_env(app)
    
    # Initialize AI Grader
    _setup_ai_grader(app)
    
    # Initialize security features
    try:
        # Initialize session security
        from .secure_auth import register_secure_auth
        session_manager = register_secure_auth(app)
        
        if session_manager:
            app.logger.info("Secure session management initialized")
        
        # Initialize socket security
        from .secure_socket_handlers import init_socket_security
        init_socket_security(redis_client)
        app.logger.info("Socket security initialized")
        
        # Initialize rate limiting
        from .rate_limiting import init_rate_limiting
        rate_limiter = init_rate_limiting(app, redis_client)
        app.logger.info("Rate limiting initialized")
        
        # Initialize database security
        from .database_security import init_database_security
        db_security_components = init_database_security(app, db)
        if db_security_components:
            app.logger.info("Database security initialized")
        
        # Initialize API security
        from .api_security import register_api_security
        api_security_components = register_api_security(app)
        if api_security_components:
            app.logger.info("API authentication and security initialized")
        
        # Initialize secrets management
        from .secrets_manager import init_secrets_management
        secrets_components = init_secrets_management(app, redis_client)
        if secrets_components:
            app.logger.info("Secrets management initialized")
        
        # Initialize game integrity
        from .game_integrity import init_game_integrity
        integrity_engine = init_game_integrity(app, redis_client)
        if integrity_engine:
            app.logger.info("Game integrity and anti-cheat system initialized")
        
        # Initialize production security if in production
        if app.config.get('ENV') == 'production':
            from .production_security import configure_production_security
            prod_security = configure_production_security(app)
            if prod_security['configured']:
                app.logger.info("Production security configuration applied")
            else:
                app.logger.error("Production security configuration failed")
        
        # Initialize security config if available
        try:
            from .security_config import create_security_manager
            security_manager = create_security_manager(app)
            app.logger.info("Advanced security features initialized")
        except ImportError:
            app.logger.info("Advanced security features not available - using basic security")
            
    except Exception as e:
        app.logger.warning(f"Security initialization failed: {e}")
        app.logger.warning("Running in basic mode without enhanced security")
    
    return app

def _get_cors_origins(env):
    """Get CORS origins based on environment"""
    if env == 'production':
        return [
            'https://csgatuntlet.com',
            'https://www.csgatuntlet.com'
        ]
    else:
        return [
            'http://localhost:3000',
            'http://localhost:3001',
            'http://127.0.0.1:3000',
            'http://127.0.0.1:3001',
            'http://localhost:5173',
            'http://127.0.0.1:5173'
        ]

def _setup_logging(app):
    """Setup application logging"""
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/csgatuntlet.log', 
            maxBytes=10240, 
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('CS Gauntlet startup')

def _register_blueprints(app):
    """Register application blueprints"""
    
    # Import blueprints
    from .auth import auth
    from .main import main
    
    # Register core blueprints
    app.register_blueprint(main)
    app.register_blueprint(auth)
    
    # Register secure OAuth blueprint if credentials available
    if app.config.get('GITHUB_CLIENT_ID') and app.config.get('GITHUB_CLIENT_SECRET'):
        try:
            from .secure_oauth import register_secure_oauth
            oauth_manager = register_secure_oauth(app)
            if oauth_manager:
                app.logger.info("Secure GitHub OAuth initialized")
            else:
                app.logger.warning("Secure OAuth registration failed")
        except Exception as e:
            app.logger.warning(f"Secure GitHub OAuth setup failed: {e}")
    else:
        app.logger.warning("GitHub OAuth credentials not found")

def _setup_user_loader(app):
    """Setup Flask-Login user loader"""
    
    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return User.query.get(int(user_id))
    
    @login_manager.unauthorized_handler
    def unauthorized():
        from flask import flash, redirect, url_for, request
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('auth.login', next=request.url))

def _setup_periodic_tasks(app):
    """Setup periodic background tasks"""
    
    def cleanup_games():
        """Periodic game cleanup"""
        with app.app_context():
            try:
                from .game_manager import game_manager
                game_manager.cleanup_inactive_games()
                app.logger.debug("Game cleanup completed")
            except Exception as e:
                app.logger.error(f"Game cleanup failed: {e}")
    
    # In production, use Celery or similar for background tasks
    # For now, games clean up themselves when accessed
    
def _setup_jinja_env(app):
    """Setup Jinja2 environment with utility functions"""
    
    # Add enumerate to Jinja2 globals
    app.jinja_env.globals.update(enumerate=enumerate)
    
    # Add custom filters
    @app.template_filter('timeago')
    def timeago_filter(dt):
        """Convert datetime to human-readable time ago"""
        if not dt:
            return 'Never'
        
        from datetime import datetime
        now = datetime.utcnow()
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"
    
    @app.template_filter('avatar')
    def avatar_filter(user, size=40):
        """Generate avatar URL for user"""
        if hasattr(user, 'avatar_url') and user.avatar_url:
            return user.avatar_url
        elif hasattr(user, 'profile_photo') and user.profile_photo != 'default-avatar.png':
            return f"/static/uploads/profile_photos/{user.profile_photo}"
        else:
            # Generate Gravatar or default avatar
            import hashlib
            email = getattr(user, 'email', 'unknown@example.com')
            hash_email = hashlib.md5(email.lower().encode()).hexdigest()
            return f"https://www.gravatar.com/avatar/{hash_email}?d=identicon&s={size}"

def _setup_ai_grader(app):
    """Setup AI Grader with Ollama integration"""
    try:
        from .ai_grader import AICodeGrader
        
        # Get configuration from environment
        ai_provider = app.config.get('AI_PROVIDER', 'ollama')
        ollama_url = app.config.get('OLLAMA_URL', 'http://localhost:11434')
        ollama_model = app.config.get('OLLAMA_MODEL', 'codellama:7b')
        openai_api_key = app.config.get('OPENAI_API_KEY')
        
        # Initialize AI grader
        ai_grader = AICodeGrader(
            ai_provider=ai_provider,
            ollama_url=ollama_url,
            ollama_model=ollama_model,
            openai_api_key=openai_api_key
        )
        
        # Store in app context for access throughout the application
        app.ai_grader = ai_grader
        
        app.logger.info(f"AI Grader initialized with {ai_provider.upper()}")
        
        # Test Ollama connection if using Ollama
        if ai_provider == 'ollama':
            import asyncio
            try:
                # Run health check in a new event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                ollama_available = loop.run_until_complete(ai_grader.check_ollama_health())
                loop.close()
                
                if ollama_available:
                    app.logger.info(f"Ollama connection successful at {ollama_url}")
                else:
                    app.logger.warning(f"Ollama not accessible at {ollama_url} - will use fallback grading")
            except Exception as e:
                app.logger.warning(f"Ollama health check failed: {e} - will use fallback grading")
        
    except Exception as e:
        app.logger.error(f"AI Grader initialization failed: {e}")
        app.ai_grader = None

# Initialize Celery if available
def create_celery(app):
    """Create Celery instance for background tasks"""
    try:
        from celery import Celery
        
        celery = Celery(
            app.import_name,
            backend=app.config.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
            broker=app.config.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
        )
        
        celery.conf.update(app.config)
        
        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)
        
        celery.Task = ContextTask
        return celery
        
    except ImportError:
        app.logger.warning("Celery not available - background tasks disabled")
        return None

# Create application factory
def create_app(config_class=None):
    """Application factory function"""
    return create_enhanced_app(config_class)

# For backward compatibility
create_app_with_security = create_enhanced_app