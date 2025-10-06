from flask import request, jsonify, g, current_app
from functools import wraps
import time
import json
import re
from typing import Dict, Any, List, Optional, Callable
from .security import SecurityValidator, SecurityAudit
from .rate_limiting import AdvancedRateLimiter

class SecurityMiddleware:
    """Comprehensive security middleware for request validation and protection"""
    
    def __init__(self, app=None):
        self.app = app
        self.blocked_ips = set()
        self.suspicious_ips = set()
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize middleware with Flask app"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        app.teardown_appcontext(self.teardown_request)
    
    def before_request(self):
        """Run before each request"""
        # Start request timing
        g.request_start_time = time.time()
        g.request_id = self._generate_request_id()
        
        # IP-based security checks
        client_ip = request.remote_addr
        if not self._check_ip_allowed(client_ip):
            SecurityAudit.log_security_event(
                'blocked_ip_access_attempt',
                ip_address=client_ip,
                details={'endpoint': request.endpoint, 'method': request.method}
            )
            return jsonify({'error': 'Access denied'}), 403
        
        # Request size validation
        if not self._validate_request_size():
            SecurityAudit.log_security_event(
                'oversized_request_blocked',
                ip_address=client_ip,
                details={'content_length': request.content_length}
            )
            return jsonify({'error': 'Request too large'}), 413
        
        # Header validation
        if not self._validate_headers():
            SecurityAudit.log_security_event(
                'malicious_headers_detected',
                ip_address=client_ip,
                details={'headers': dict(request.headers)}
            )
            return jsonify({'error': 'Invalid request headers'}), 400
        
        # Path traversal protection
        if not self._validate_path():
            SecurityAudit.log_security_event(
                'path_traversal_attempt',
                ip_address=client_ip,
                details={'path': request.path, 'full_path': request.full_path}
            )
            return jsonify({'error': 'Invalid request path'}), 400
    
    def after_request(self, response):
        """Run after each request"""
        # Add security headers
        response = self._add_security_headers(response)
        
        # Log request completion
        if hasattr(g, 'request_start_time'):
            request_time = time.time() - g.request_start_time
            
            # Log slow requests
            if request_time > 5.0:  # 5 seconds
                SecurityAudit.log_security_event(
                    'slow_request_detected',
                    details={
                        'request_time': request_time,
                        'endpoint': request.endpoint,
                        'method': request.method
                    }
                )
        
        return response
    
    def teardown_request(self, exception):
        """Clean up after request"""
        if exception:
            SecurityAudit.log_security_event(
                'request_exception',
                details={
                    'exception': str(exception),
                    'endpoint': request.endpoint,
                    'method': request.method
                }
            )
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _check_ip_allowed(self, ip: str) -> bool:
        """Check if IP address is allowed"""
        if ip in self.blocked_ips:
            return False
        
        # Check for private/local IPs in production
        if current_app.config.get('ENV') == 'production':
            import ipaddress
            try:
                ip_obj = ipaddress.ip_address(ip)
                if ip_obj.is_private and ip != '127.0.0.1':
                    return False
            except ValueError:
                return False
        
        return True
    
    def _validate_request_size(self) -> bool:
        """Validate request size limits"""
        max_content_length = current_app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)
        
        if request.content_length and request.content_length > max_content_length:
            return False
        
        return True
    
    def _validate_headers(self) -> bool:
        """Validate request headers for security issues"""
        dangerous_patterns = [
            r'<script[^>]*>',
            r'javascript:',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*=',
            r'eval\s*\(',
            r'expression\s*\(',
        ]
        
        for header_name, header_value in request.headers:
            # Check header names
            if not re.match(r'^[a-zA-Z0-9\-_]+$', header_name):
                return False
            
            # Check header values for malicious content
            for pattern in dangerous_patterns:
                if re.search(pattern, str(header_value), re.IGNORECASE):
                    return False
            
            # Check for excessively long headers
            if len(str(header_value)) > 8192:  # 8KB limit per header
                return False
        
        return True
    
    def _validate_path(self) -> bool:
        """Validate request path for security issues"""
        path = request.path
        
        # Check for path traversal attempts
        if '..' in path or '~' in path:
            return False
        
        # Check for null bytes
        if '\x00' in path:
            return False
        
        # Check for encoded path traversal
        dangerous_encoded = ['%2e%2e', '%2f%2e%2e', '%5c%2e%2e', '%252e%252e']
        path_lower = path.lower()
        for encoded in dangerous_encoded:
            if encoded in path_lower:
                return False
        
        return True
    
    def _add_security_headers(self, response):
        """Add security headers to response"""
        # Content Security Policy
        csp = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'none';"
        response.headers['Content-Security-Policy'] = csp
        
        # Other security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # HSTS for HTTPS
        if request.is_secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        # Remove server identification
        response.headers.pop('Server', None)
        
        return response

class RequestValidator:
    """Request validation decorator and utilities"""
    
    @staticmethod
    def validate_json_request(required_fields: List[str] = None, 
                            optional_fields: List[str] = None,
                            validation_schema: Dict[str, Dict] = None):
        """Decorator to validate JSON request data"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not request.is_json:
                    return jsonify({'error': 'Request must be JSON'}), 400
                
                try:
                    data = request.get_json()
                except Exception:
                    return jsonify({'error': 'Invalid JSON'}), 400
                
                if data is None:
                    return jsonify({'error': 'No JSON data provided'}), 400
                
                # Check required fields
                if required_fields:
                    missing_fields = [field for field in required_fields if field not in data]
                    if missing_fields:
                        return jsonify({
                            'error': f'Missing required fields: {", ".join(missing_fields)}'
                        }), 400
                
                # Validate against schema if provided
                if validation_schema:
                    for field, rules in validation_schema.items():
                        if field in data:
                            value = data[field]
                            
                            # Type validation
                            if 'type' in rules:
                                expected_type = rules['type']
                                if expected_type == 'string' and not isinstance(value, str):
                                    return jsonify({'error': f'{field} must be a string'}), 400
                                elif expected_type == 'integer' and not isinstance(value, int):
                                    return jsonify({'error': f'{field} must be an integer'}), 400
                                elif expected_type == 'boolean' and not isinstance(value, bool):
                                    return jsonify({'error': f'{field} must be a boolean'}), 400
                                elif expected_type == 'list' and not isinstance(value, list):
                                    return jsonify({'error': f'{field} must be a list'}), 400
                            
                            # Length validation
                            if 'max_length' in rules and isinstance(value, str):
                                if len(value) > rules['max_length']:
                                    return jsonify({
                                        'error': f'{field} exceeds maximum length of {rules["max_length"]}'
                                    }), 400
                            
                            # Custom validation
                            if 'validator' in rules:
                                validator_func = rules['validator']
                                if not validator_func(value):
                                    return jsonify({
                                        'error': f'{field} failed validation'
                                    }), 400
                            
                            # Sanitization
                            if isinstance(value, str):
                                data[field] = SecurityValidator.sanitize_text(value, rules.get('max_length', 1000))
                
                # Remove unexpected fields if specified
                if required_fields or optional_fields:
                    allowed_fields = set((required_fields or []) + (optional_fields or []))
                    data = {k: v for k, v in data.items() if k in allowed_fields}
                
                # Store validated data
                g.validated_data = data
                return f(*args, **kwargs)
            
            return decorated_function
        return decorator
    
    @staticmethod
    def validate_form_request(validation_schema: Dict[str, Dict]):
        """Decorator to validate form request data"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                data = request.form.to_dict()
                
                # Validate against schema
                for field, rules in validation_schema.items():
                    if field in data:
                        value = data[field]
                        
                        # Required field check
                        if rules.get('required', False) and not value:
                            return jsonify({'error': f'{field} is required'}), 400
                        
                        # Type and format validation
                        if 'pattern' in rules:
                            pattern_name = rules['pattern']
                            is_valid, error_msg = SecurityValidator.validate_input(
                                value, pattern_name, rules.get('required', False)
                            )
                            if not is_valid:
                                return jsonify({'error': error_msg}), 400
                        
                        # Sanitization
                        if isinstance(value, str):
                            data[field] = SecurityValidator.sanitize_text(
                                value, rules.get('max_length', 1000)
                            )
                
                g.validated_data = data
                return f(*args, **kwargs)
            
            return decorated_function
        return decorator

class CSRFProtection:
    """CSRF protection middleware"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize CSRF protection"""
        app.before_request(self.protect)
    
    def protect(self):
        """CSRF protection check"""
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            # Skip CSRF for API endpoints with proper authentication
            if request.path.startswith('/api/') and self._has_valid_auth():
                return
            
            # Check CSRF token
            token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
            if not token or not self._validate_csrf_token(token):
                SecurityAudit.log_security_event(
                    'csrf_validation_failed',
                    details={'endpoint': request.endpoint, 'method': request.method}
                )
                return jsonify({'error': 'CSRF token missing or invalid'}), 403
    
    def _has_valid_auth(self) -> bool:
        """Check if request has valid authentication"""
        # Check for JWT or session authentication
        return (request.headers.get('Authorization') or 
                hasattr(request, 'current_user') and request.current_user)
    
    def _validate_csrf_token(self, token: str) -> bool:
        """Validate CSRF token"""
        # Implement CSRF token validation logic
        # This is a simplified implementation
        from flask import session
        return session.get('csrf_token') == token

def create_validation_middleware(app):
    """Create and register all validation middleware"""
    
    # Security middleware
    security_middleware = SecurityMiddleware(app)
    
    # CSRF protection
    csrf_protection = CSRFProtection(app)
    
    return {
        'security': security_middleware,
        'csrf': csrf_protection
    }

# Common validation schemas
COMMON_SCHEMAS = {
    'user_login': {
        'email': {'type': 'string', 'pattern': 'email', 'required': True, 'max_length': 100},
        'password': {'type': 'string', 'required': True, 'max_length': 200}
    },
    'user_register': {
        'username': {'type': 'string', 'pattern': 'username', 'required': True, 'max_length': 20},
        'email': {'type': 'string', 'pattern': 'email', 'required': True, 'max_length': 100},
        'password': {'type': 'string', 'required': True, 'max_length': 200},
        'college_name': {'type': 'string', 'pattern': 'college_name', 'required': False, 'max_length': 100}
    },
    'code_submission': {
        'code': {'type': 'string', 'required': True, 'max_length': 50000},
        'language': {'type': 'string', 'pattern': 'language', 'required': True},
        'problem_id': {'type': 'string', 'required': True, 'max_length': 50}
    },
    'profile_update': {
        'username': {'type': 'string', 'pattern': 'username', 'required': False, 'max_length': 20},
        'bio': {'type': 'string', 'required': False, 'max_length': 500},
        'github_username': {'type': 'string', 'pattern': 'github_username', 'required': False, 'max_length': 39}
    }
}

# Convenience decorators
validate_login = RequestValidator.validate_json_request(
    validation_schema=COMMON_SCHEMAS['user_login']
)

validate_registration = RequestValidator.validate_json_request(
    validation_schema=COMMON_SCHEMAS['user_register']
)

validate_code_submission = RequestValidator.validate_json_request(
    validation_schema=COMMON_SCHEMAS['code_submission']
)

validate_profile_update = RequestValidator.validate_json_request(
    validation_schema=COMMON_SCHEMAS['profile_update']
)