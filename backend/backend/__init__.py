from flask import Flask, flash, redirect, url_for
from flask_socketio import SocketIO
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_redis import FlaskRedis
import os
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
from flask_cors import CORS
from config import Config, DevelopmentConfig, TestingConfig, ProductionConfig
from celery_app import celery_app
from .cors_config import setup_secure_cors, SecureCORSConfig

# Import security modules
try:
    from .security_config import create_security_manager
    from .middleware import SecurityMiddleware, RequestValidator, CSRFProtection
    from .rate_limiting import setup_rate_limiting
    from .security_headers import setup_security_headers
    from .audit_logger import setup_audit_logging, AuditEventType, AuditSeverity
    from .secure_code_executor import SecureCodeExecutor
    from .secure_upload import SecureFileUpload
    SECURITY_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Security modules not fully available: {e}")
    SECURITY_AVAILABLE = False

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
redis_client = FlaskRedis()
socketio = SocketIO(
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1e8,
    logger=True,
    engineio_logger=True
)
login_manager = LoginManager()

# Global AI grader instance
ai_grader = None

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # GitHub OAuth config
    if not app.config['GITHUB_CLIENT_ID'] or not app.config['GITHUB_CLIENT_SECRET']:
        print("Warning: GitHub OAuth credentials not found in .env file")

    # Production settings
    if isinstance(config_class, type) and issubclass(config_class, ProductionConfig):
        # Configure logging
        handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3)
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)
    
    # Setup secure CORS for Flask routes
    try:
        setup_secure_cors(app)
    except Exception as e:
        # Do not crash app on CORS init issues, but log for visibility
        app.logger.warning(f"Failed to initialize secure CORS: {e}")
    
    # Initialize security features if available
    if SECURITY_AVAILABLE:
        try:
            # Initialize security manager
            security_manager = create_security_manager(app)
            app.security_manager = security_manager
            
            # Setup rate limiting
            setup_rate_limiting(app)
            
            # Setup security headers
            setup_security_headers(app)
            
            # Setup audit logging
            setup_audit_logging(app)
            
            app.logger.info("Security features initialized successfully")
        except Exception as e:
            app.logger.warning(f"Failed to initialize security features: {e}")
    else:
        app.logger.warning("Security features not available - running in basic mode")

    # Determine allowed origins for Socket.IO to align with Flask CORS
    allowed_origins_env = os.getenv('CORS_ALLOWED_ORIGINS')
    if allowed_origins_env:
        allowed_origins = [o.strip() for o in allowed_origins_env.split(',') if o.strip()]
    else:
        # Use the same origin lists defined in SecureCORSConfig
        cors_helper = SecureCORSConfig()
        env = app.config.get('ENV', 'development')
        if env == 'production':
            cors_cfg = cors_helper._get_production_cors_config()
        elif env == 'staging':
            cors_cfg = cors_helper._get_staging_cors_config()
        else:
            cors_cfg = cors_helper._get_development_cors_config()
        allowed_origins = cors_cfg.get('origins', [])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    redis_client.init_app(app)
    # Align Socket.IO CORS with Flask CORS configuration
    socketio.init_app(app, cors_allowed_origins=allowed_origins)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Initialize Celery with the Flask app context
    celery_app.conf.update(app.config)
    celery_app.app = app

    # Add enumerate to Jinja2 environment
    app.jinja_env.globals.update(enumerate=enumerate)

    # Initialize AI Grader
    _setup_ai_grader(app)

    # Import models to ensure they're registered with SQLAlchemy
    from .models import User, OAuth, Score, Problem, Submission, GameModeDetails, TriviaQuestion, DebugChallenge

    # Import socket events
    from . import socket_handlers
    # Ensure game-related socket handlers are registered
    try:
        from . import game_socket_handlers  # noqa: F401
    except Exception as e:
        app.logger.warning(f"Failed to import game_socket_handlers: {e}")

    # Register blueprints
    from .auth import auth
    from .main import main
    from .game_api import game_api
    from .oauth import make_github_blueprint
    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(game_api)
    
    # Only register GitHub blueprint if credentials are available
    if app.config['GITHUB_CLIENT_ID'] and app.config['GITHUB_CLIENT_SECRET']:
        github_bp = make_github_blueprint(app)
        app.register_blueprint(github_bp, url_prefix="/login")

    # Register user loader
    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return User.query.get(int(user_id))

    return app

def _setup_ai_grader(app):
    """Setup AI Grader with Ollama integration"""
    global ai_grader
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
        ai_grader = None
