from flask import request, current_app
from flask_cors import CORS
from typing import List, Dict, Optional
import re
from .security import SecurityAudit

class SecureCORSConfig:
    """Secure CORS configuration with environment-specific settings"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize CORS with secure configuration"""
        
        # Get environment
        env = app.config.get('ENV', 'development')
        
        if env == 'production':
            cors_config = self._get_production_cors_config()
        elif env == 'staging':
            cors_config = self._get_staging_cors_config()
        else:
            cors_config = self._get_development_cors_config()
        
        # Apply CORS configuration
        CORS(app, **cors_config)
        
        # Add custom CORS validation
        app.before_request(self._validate_cors_request)
    
    def _get_production_cors_config(self) -> Dict:
        """Production CORS configuration - most restrictive"""
        
        # Define allowed origins for production
        allowed_origins = [
            "https://csgatuntlet.com",
            "https://www.csgatuntlet.com",
            "https://app.csgatuntlet.com",
            # Add your production domains here
        ]
        
        return {
            'origins': allowed_origins,
            'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
            'allow_headers': [
                'Content-Type',
                'Authorization',
                'X-Requested-With',
                'X-CSRF-Token',
                'X-Request-ID'
            ],
            'expose_headers': [
                'X-Request-ID',
                'X-RateLimit-Remaining',
                'X-RateLimit-Reset'
            ],
            'supports_credentials': True,
            'max_age': 86400,  # 24 hours
            'vary_header': True,
            'automatic_options': True
        }
    
    def _get_staging_cors_config(self) -> Dict:
        """Staging CORS configuration - moderate restrictions"""
        
        allowed_origins = [
            "https://staging.csgatuntlet.com",
            "https://test.csgatuntlet.com",
            "https://dev.csgatuntlet.com",
            # Staging domains
        ]
        
        return {
            'origins': allowed_origins,
            'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
            'allow_headers': [
                'Content-Type',
                'Authorization',
                'X-Requested-With',
                'X-CSRF-Token',
                'X-Request-ID',
                'X-Debug-Mode'
            ],
            'expose_headers': [
                'X-Request-ID',
                'X-RateLimit-Remaining',
                'X-RateLimit-Reset',
                'X-Debug-Info'
            ],
            'supports_credentials': True,
            'max_age': 3600,  # 1 hour
            'vary_header': True,
            'automatic_options': True
        }
    
    def _get_development_cors_config(self) -> Dict:
        """Development CORS configuration - relaxed for local development"""
        
        return {
            'origins': [
                "http://localhost:3000",
                "http://localhost:3001",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:3001",
                "http://localhost:5173",  # Vite default
                "http://127.0.0.1:5173"
            ],
            'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
            'allow_headers': [
                'Content-Type',
                'Authorization',
                'X-Requested-With',
                'X-CSRF-Token',
                'X-Request-ID',
                'X-Debug-Mode',
                'Accept',
                'Origin'
            ],
            'expose_headers': [
                'X-Request-ID',
                'X-RateLimit-Remaining',
                'X-RateLimit-Reset',
                'X-Debug-Info'
            ],
            'supports_credentials': True,
            'max_age': 600,  # 10 minutes
            'vary_header': True,
            'automatic_options': True
        }
    
    def _validate_cors_request(self):
        """Additional CORS validation beyond Flask-CORS"""
        
        origin = request.headers.get('Origin')
        if not origin:
            return  # No origin header, likely same-origin request
        
        # Log cross-origin requests
        SecurityAudit.log_security_event(
            'cors_request',
            details={
                'origin': origin,
                'endpoint': request.endpoint,
                'method': request.method,
                'user_agent': request.headers.get('User-Agent', '')
            }
        )
        
        # Validate origin format
        if not self._is_valid_origin_format(origin):
            SecurityAudit.log_security_event(
                'invalid_origin_format',
                details={'origin': origin}
            )
            return
        
        # Check for suspicious origins
        if self._is_suspicious_origin(origin):
            SecurityAudit.log_security_event(
                'suspicious_cors_origin',
                details={'origin': origin, 'reason': 'suspicious pattern detected'}
            )
    
    def _is_valid_origin_format(self, origin: str) -> bool:
        """Validate origin URL format"""
        
        # Basic URL format validation
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
            r'(?::\d+)?'  # optional port
            r'$', re.IGNORECASE
        )
        
        return bool(url_pattern.match(origin))
    
    def _is_suspicious_origin(self, origin: str) -> bool:
        """Check if origin matches suspicious patterns"""
        
        suspicious_patterns = [
            r'.*\.ngrok\.io$',  # Tunnel services (might be legitimate in dev)
            r'.*\.herokuapp\.com$',  # Heroku (might be legitimate)
            r'.*\.repl\.co$',  # Repl.it
            r'.*\.glitch\.me$',  # Glitch
            r'.*\.now\.sh$',  # Vercel
            r'.*\.netlify\.app$',  # Netlify (might be legitimate)
            r'.*\.github\.io$',  # GitHub Pages
            r'.*\.surge\.sh$',  # Surge.sh
            r'.*localhost:\d{4,5}$',  # High port localhost (might be suspicious)
            r'.*\.onion$',  # Tor hidden services
            r'.*\.(tk|ml|ga|cf)$',  # Free domains often used maliciously
        ]
        
        # In production, be more strict
        if current_app.config.get('ENV') == 'production':
            for pattern in suspicious_patterns:
                if re.match(pattern, origin, re.IGNORECASE):
                    return True
        
        # Check for obviously malicious patterns
        malicious_patterns = [
            r'.*evil.*',
            r'.*hack.*',
            r'.*malware.*',
            r'.*phish.*',
            r'.*spam.*',
            r'.*\.bit$',  # Some blockchain domains
        ]
        
        for pattern in malicious_patterns:
            if re.search(pattern, origin, re.IGNORECASE):
                return True
        
        return False

class OriginValidator:
    """Advanced origin validation for API endpoints"""
    
    def __init__(self):
        self.trusted_origins = set()
        self.blocked_origins = set()
        self.origin_patterns = {}
    
    def add_trusted_origin(self, origin: str):
        """Add a trusted origin"""
        self.trusted_origins.add(origin.lower())
    
    def add_trusted_pattern(self, pattern_name: str, pattern: str):
        """Add a trusted origin pattern"""
        self.origin_patterns[pattern_name] = re.compile(pattern, re.IGNORECASE)
    
    def block_origin(self, origin: str):
        """Block a specific origin"""
        self.blocked_origins.add(origin.lower())
    
    def validate_origin(self, origin: str) -> bool:
        """Validate if origin is allowed"""
        
        if not origin:
            return True  # No origin header (same-origin)
        
        origin_lower = origin.lower()
        
        # Check blocked list
        if origin_lower in self.blocked_origins:
            return False
        
        # Check trusted list
        if origin_lower in self.trusted_origins:
            return True
        
        # Check patterns
        for pattern_name, pattern in self.origin_patterns.items():
            if pattern.match(origin):
                return True
        
        return False

def validate_origin(allowed_origins: List[str] = None):
    """Decorator to validate request origin"""
    
    def decorator(f):
        def decorated_function(*args, **kwargs):
            origin = request.headers.get('Origin')
            
            if origin and allowed_origins:
                if origin not in allowed_origins:
                    SecurityAudit.log_security_event(
                        'unauthorized_origin_blocked',
                        details={'origin': origin, 'endpoint': request.endpoint}
                    )
                    from flask import jsonify
                    return jsonify({'error': 'Origin not allowed'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

class CORSSecurityMonitor:
    """Monitor CORS requests for security analysis"""
    
    def __init__(self, app=None):
        self.app = app
        self.origin_stats = {}
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize CORS monitoring"""
        app.after_request(self.monitor_cors_response)
    
    def monitor_cors_response(self, response):
        """Monitor CORS responses"""
        
        origin = request.headers.get('Origin')
        if origin:
            # Track origin usage
            self.origin_stats[origin] = self.origin_stats.get(origin, 0) + 1
            
            # Check for unusual CORS headers in response
            cors_headers = [
                'Access-Control-Allow-Origin',
                'Access-Control-Allow-Methods',
                'Access-Control-Allow-Headers',
                'Access-Control-Allow-Credentials'
            ]
            
            for header in cors_headers:
                if header in response.headers:
                    value = response.headers[header]
                    
                    # Monitor for overly permissive CORS
                    if header == 'Access-Control-Allow-Origin' and value == '*':
                        if 'Access-Control-Allow-Credentials' in response.headers:
                            SecurityAudit.log_security_event(
                                'dangerous_cors_configuration',
                                details={
                                    'reason': 'Wildcard origin with credentials',
                                    'origin': origin
                                }
                            )
        
        return response
    
    def get_origin_stats(self) -> Dict[str, int]:
        """Get origin usage statistics"""
        return self.origin_stats.copy()

def setup_secure_cors(app):
    """Setup comprehensive CORS security"""
    
    # Main CORS configuration
    cors_config = SecureCORSConfig(app)
    
    # CORS monitoring
    cors_monitor = CORSSecurityMonitor(app)
    
    # Origin validator for custom validation
    origin_validator = OriginValidator()
    
    # Add common trusted patterns for development
    if app.config.get('ENV') != 'production':
        origin_validator.add_trusted_pattern(
            'localhost', r'^https?://localhost:\d+$'
        )
        origin_validator.add_trusted_pattern(
            'local_ip', r'^https?://127\.0\.0\.1:\d+$'
        )
    
    # Store validator in app for use in routes
    app.origin_validator = origin_validator
    
    return {
        'config': cors_config,
        'monitor': cors_monitor,
        'validator': origin_validator
    }

# Environment-specific CORS configurations
CORS_CONFIGS = {
    'development': {
        'origins': ['http://localhost:3000', 'http://127.0.0.1:3000'],
        'strict': False
    },
    'staging': {
        'origins': ['https://staging.csgatuntlet.com'],
        'strict': True
    },
    'production': {
        'origins': ['https://csgatuntlet.com', 'https://www.csgatuntlet.com'],
        'strict': True
    }
}