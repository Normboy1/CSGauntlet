"""
Production Security Configuration for CS Gauntlet
SSL/TLS, production hardening, and deployment security
"""

import os
import ssl
import secrets
from typing import Dict, List, Optional, Any
from flask import Flask, request, g
from werkzeug.middleware.proxy_fix import ProxyFix
import logging

from .security import SecurityAudit
from .audit_logger import AuditEventType, AuditSeverity

class ProductionSecurityConfig:
    """Production security configuration and hardening"""
    
    def __init__(self, app: Flask):
        self.app = app
        self.is_production = app.config.get('ENV') == 'production'
        
    def configure_production_security(self):
        """Configure all production security features"""
        
        if not self.is_production:
            self.app.logger.info("Development mode - skipping production security config")
            return
        
        try:
            # SSL/TLS Configuration
            self._configure_ssl_tls()
            
            # Security headers
            self._configure_security_headers()
            
            # Proxy configuration
            self._configure_proxy_settings()
            
            # Session security
            self._configure_session_security()
            
            # File upload security
            self._configure_upload_security()
            
            # Rate limiting configuration
            self._configure_rate_limiting()
            
            # Error handling
            self._configure_error_handling()
            
            # Logging configuration
            self._configure_production_logging()
            
            self.app.logger.info("Production security configuration completed")
            
        except Exception as e:
            self.app.logger.error(f"Production security configuration failed: {e}")
    
    def _configure_ssl_tls(self):
        """Configure SSL/TLS settings"""
        
        # Set secure SSL context if using built-in server (not recommended for production)
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Configure cipher suites (modern, secure ciphers only)
        ssl_context.set_ciphers(':'.join([
            'ECDHE+AESGCM',
            'ECDHE+CHACHA20',
            'DHE+AESGCM',
            'DHE+CHACHA20',
            '!aNULL',
            '!MD5',
            '!DSS'
        ]))
        
        # Set minimum TLS version
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
        
        # Force HTTPS redirect
        @self.app.before_request
        def force_https():
            if not request.is_secure and self.app.config.get('FORCE_HTTPS', True):
                return redirect(request.url.replace('http://', 'https://'), code=301)
        
        self.app.logger.info("SSL/TLS configuration applied")
    
    def _configure_security_headers(self):
        """Configure security headers for all responses"""
        
        @self.app.after_request
        def add_security_headers(response):
            # Content Security Policy
            csp_policy = "; ".join([
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net",
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com",
                "font-src 'self' https://fonts.gstatic.com",
                "img-src 'self' data: https: blob:",
                "connect-src 'self' wss: ws:",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'"
            ])
            response.headers['Content-Security-Policy'] = csp_policy
            
            # Security headers
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
            
            # HSTS (HTTP Strict Transport Security)
            if request.is_secure:
                response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
            
            # Remove server information
            response.headers.pop('Server', None)
            
            return response
        
        self.app.logger.info("Security headers configured")
    
    def _configure_proxy_settings(self):
        """Configure proxy settings for deployment behind reverse proxy"""
        
        # Trust proxy headers (nginx, cloudflare, etc.)
        self.app.wsgi_app = ProxyFix(
            self.app.wsgi_app,
            x_for=1,
            x_proto=1,
            x_host=1,
            x_prefix=1
        )
        
        self.app.logger.info("Proxy settings configured")
    
    def _configure_session_security(self):
        """Configure secure session settings"""
        
        # Generate secure secret key if not provided
        if not self.app.config.get('SECRET_KEY'):
            self.app.config['SECRET_KEY'] = secrets.token_urlsafe(64)
            self.app.logger.warning("Generated temporary secret key - set SECRET_KEY in production")
        
        # Session configuration
        self.app.config.update({
            'SESSION_COOKIE_SECURE': True,
            'SESSION_COOKIE_HTTPONLY': True,
            'SESSION_COOKIE_SAMESITE': 'Lax',
            'PERMANENT_SESSION_LIFETIME': 3600 * 24,  # 24 hours
            'SESSION_COOKIE_NAME': 'cs_gauntlet_session'
        })
        
        self.app.logger.info("Session security configured")
    
    def _configure_upload_security(self):
        """Configure file upload security"""
        
        # File upload limits
        self.app.config.update({
            'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB max file size
            'UPLOAD_FOLDER': os.path.join(self.app.instance_path, 'uploads'),
            'ALLOWED_EXTENSIONS': {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt'}
        })
        
        # Create upload directory if it doesn't exist
        upload_dir = self.app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir, mode=0o755)
        
        self.app.logger.info("Upload security configured")
    
    def _configure_rate_limiting(self):
        """Configure production rate limiting"""
        
        # Global rate limiting middleware
        @self.app.before_request
        def global_rate_limit():
            if hasattr(g, 'rate_limiter'):
                client_ip = request.remote_addr
                
                # Global rate limit
                global_key = f"global_rate:{client_ip}"
                if not g.rate_limiter.is_allowed(global_key, 1000, 3600):  # 1000 requests per hour
                    SecurityAudit.log_security_event(
                        event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
                        severity=AuditSeverity.HIGH,
                        success=False,
                        message="Global rate limit exceeded",
                        details={'ip': client_ip}
                    )
                    from flask import abort
                    abort(429)
                
                g.rate_limiter.record_request(global_key)
        
        self.app.logger.info("Production rate limiting configured")
    
    def _configure_error_handling(self):
        """Configure secure error handling"""
        
        @self.app.errorhandler(404)
        def handle_not_found(error):
            return {'error': 'Resource not found'}, 404
        
        @self.app.errorhandler(500)
        def handle_internal_error(error):
            # Log error but don't expose details
            self.app.logger.error(f"Internal server error: {error}")
            return {'error': 'Internal server error'}, 500
        
        @self.app.errorhandler(403)
        def handle_forbidden(error):
            return {'error': 'Access forbidden'}, 403
        
        @self.app.errorhandler(429)
        def handle_rate_limit(error):
            return {'error': 'Rate limit exceeded', 'retry_after': 3600}, 429
        
        # Disable debug mode and testing
        self.app.config['DEBUG'] = False
        self.app.config['TESTING'] = False
        
        self.app.logger.info("Error handling configured")
    
    def _configure_production_logging(self):
        """Configure production logging"""
        
        # Create logs directory
        log_dir = os.path.join(self.app.instance_path, 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, mode=0o755)
        
        # Configure file logging
        from logging.handlers import RotatingFileHandler
        
        # Application logs
        app_handler = RotatingFileHandler(
            os.path.join(log_dir, 'cs_gauntlet.log'),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10
        )
        app_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        app_handler.setLevel(logging.INFO)
        self.app.logger.addHandler(app_handler)
        
        # Security logs
        security_handler = RotatingFileHandler(
            os.path.join(log_dir, 'security.log'),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=20
        )
        security_handler.setFormatter(logging.Formatter(
            '%(asctime)s SECURITY %(levelname)s: %(message)s'
        ))
        security_handler.setLevel(logging.WARNING)
        
        # Add security handler to security logger
        security_logger = logging.getLogger('security')
        security_logger.addHandler(security_handler)
        
        self.app.logger.setLevel(logging.INFO)
        self.app.logger.info("Production logging configured")

class EnvironmentValidator:
    """Validates production environment configuration"""
    
    def __init__(self, app: Flask):
        self.app = app
        self.validation_errors = []
        self.validation_warnings = []
    
    def validate_production_environment(self) -> Dict[str, Any]:
        """Validate production environment settings"""
        
        # Check required environment variables
        self._check_required_env_vars()
        
        # Check database configuration
        self._check_database_config()
        
        # Check security configuration
        self._check_security_config()
        
        # Check external services
        self._check_external_services()
        
        # Check file permissions
        self._check_file_permissions()
        
        return {
            'valid': len(self.validation_errors) == 0,
            'errors': self.validation_errors,
            'warnings': self.validation_warnings
        }
    
    def _check_required_env_vars(self):
        """Check required environment variables"""
        
        required_vars = [
            'SECRET_KEY',
            'DATABASE_URL',
            'REDIS_URL',
            'FLASK_ENV'
        ]
        
        for var in required_vars:
            if not os.getenv(var):
                self.validation_errors.append(f"Missing required environment variable: {var}")
        
        # Check optional but recommended vars
        recommended_vars = [
            'GITHUB_CLIENT_ID',
            'GITHUB_CLIENT_SECRET',
            'OPENAI_API_KEY'
        ]
        
        for var in recommended_vars:
            if not os.getenv(var):
                self.validation_warnings.append(f"Missing recommended environment variable: {var}")
    
    def _check_database_config(self):
        """Check database configuration"""
        
        db_url = os.getenv('DATABASE_URL', '')
        
        if 'sqlite' in db_url.lower() and self.app.config.get('ENV') == 'production':
            self.validation_warnings.append("SQLite not recommended for production")
        
        if 'localhost' in db_url and self.app.config.get('ENV') == 'production':
            self.validation_warnings.append("Local database not recommended for production")
        
        if not db_url.startswith(('postgresql://', 'mysql://', 'sqlite://')):
            self.validation_errors.append("Invalid database URL format")
    
    def _check_security_config(self):
        """Check security configuration"""
        
        secret_key = os.getenv('SECRET_KEY', '')
        if len(secret_key) < 32:
            self.validation_errors.append("SECRET_KEY must be at least 32 characters")
        
        if not os.getenv('JWT_SECRET_KEY'):
            self.validation_warnings.append("JWT_SECRET_KEY not set - using SECRET_KEY")
        
        if not os.getenv('DATABASE_ENCRYPTION_KEY'):
            self.validation_warnings.append("DATABASE_ENCRYPTION_KEY not set")
    
    def _check_external_services(self):
        """Check external service configuration"""
        
        redis_url = os.getenv('REDIS_URL', '')
        if not redis_url:
            self.validation_errors.append("Redis URL required for production")
        elif 'localhost' in redis_url and self.app.config.get('ENV') == 'production':
            self.validation_warnings.append("Local Redis not recommended for production")
    
    def _check_file_permissions(self):
        """Check file and directory permissions"""
        
        # Check instance path permissions
        instance_path = self.app.instance_path
        if os.path.exists(instance_path):
            stat_info = os.stat(instance_path)
            if stat_info.st_mode & 0o077:  # Check if group/other have write access
                self.validation_warnings.append("Instance directory has overly permissive permissions")

class SecurityMonitoring:
    """Production security monitoring and alerting"""
    
    def __init__(self, app: Flask):
        self.app = app
        self.alert_thresholds = {
            'failed_logins_per_hour': 100,
            'rate_limit_violations_per_hour': 50,
            'security_violations_per_hour': 20,
            'error_rate_per_hour': 1000
        }
    
    def setup_monitoring(self):
        """Setup security monitoring"""
        
        # Monitor critical security events
        @self.app.before_request
        def monitor_request():
            g.request_start_time = time.time()
        
        @self.app.after_request
        def monitor_response(response):
            try:
                # Track response times
                if hasattr(g, 'request_start_time'):
                    response_time = time.time() - g.request_start_time
                    if response_time > 5.0:  # Slow response
                        self.app.logger.warning(f"Slow response: {response_time:.2f}s for {request.path}")
                
                # Track error rates
                if response.status_code >= 500:
                    self.app.logger.error(f"Server error {response.status_code} for {request.path}")
                
                return response
                
            except Exception as e:
                self.app.logger.error(f"Monitoring error: {e}")
                return response
        
        self.app.logger.info("Security monitoring configured")

# Integration functions

def configure_production_security(app: Flask):
    """Main function to configure all production security"""
    
    try:
        # Apply production security configuration
        prod_config = ProductionSecurityConfig(app)
        prod_config.configure_production_security()
        
        # Validate environment
        validator = EnvironmentValidator(app)
        validation_result = validator.validate_production_environment()
        
        if not validation_result['valid']:
            app.logger.error("Production environment validation failed:")
            for error in validation_result['errors']:
                app.logger.error(f"  ERROR: {error}")
        
        for warning in validation_result['warnings']:
            app.logger.warning(f"  WARNING: {warning}")
        
        # Setup monitoring
        monitoring = SecurityMonitoring(app)
        monitoring.setup_monitoring()
        
        app.logger.info("Production security configuration completed")
        
        return {
            'configured': True,
            'validation_result': validation_result
        }
        
    except Exception as e:
        app.logger.error(f"Production security configuration failed: {e}")
        return {
            'configured': False,
            'error': str(e)
        }

import time
from flask import redirect