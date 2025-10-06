from flask import request, current_app, g
from typing import Dict, List, Optional, Callable
import time
from .security import SecurityAudit

class SecurityHeaders:
    """Comprehensive security headers middleware"""
    
    def __init__(self, app=None):
        self.app = app
        self.custom_headers = {}
        self.conditional_headers = {}
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize security headers middleware"""
        app.after_request(self.add_security_headers)
    
    def add_security_headers(self, response):
        """Add comprehensive security headers to all responses"""
        
        # Get environment-specific configuration
        env = current_app.config.get('ENV', 'development')
        is_https = request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https'
        
        # Core security headers
        self._add_core_headers(response, env, is_https)
        
        # Content security headers
        self._add_content_security_headers(response, env)
        
        # Privacy and tracking headers
        self._add_privacy_headers(response)
        
        # Performance and caching headers
        self._add_performance_headers(response)
        
        # Custom headers
        self._add_custom_headers(response)
        
        # Conditional headers
        self._add_conditional_headers(response)
        
        # Log security header application
        if current_app.config.get('LOG_SECURITY_HEADERS', False):
            self._log_headers_applied(response)
        
        return response
    
    def _add_core_headers(self, response, env: str, is_https: bool):
        """Add core security headers"""
        
        # X-Content-Type-Options: Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # X-Frame-Options: Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        
        # X-XSS-Protection: Enable XSS filtering (legacy browsers)
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer-Policy: Control referrer information
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # X-Permitted-Cross-Domain-Policies: Disable Adobe Flash/PDF cross-domain
        response.headers['X-Permitted-Cross-Domain-Policies'] = 'none'
        
        # X-Download-Options: Prevent IE from executing downloads
        response.headers['X-Download-Options'] = 'noopen'
        
        # Strict-Transport-Security: Enforce HTTPS
        if is_https:
            if env == 'production':
                response.headers['Strict-Transport-Security'] = (
                    'max-age=31536000; includeSubDomains; preload'
                )
            else:
                response.headers['Strict-Transport-Security'] = (
                    'max-age=3600; includeSubDomains'
                )
        
        # Expect-CT: Certificate Transparency (HTTPS only)
        if is_https and env == 'production':
            response.headers['Expect-CT'] = (
                'max-age=86400, enforce, '
                'report-uri="https://csgatuntlet.com/ct-report"'
            )
    
    def _add_content_security_headers(self, response, env: str):
        """Add Content Security Policy and related headers"""
        
        # Build CSP based on environment
        csp_directives = self._build_csp_directives(env)
        csp_header = '; '.join([f"{directive} {' '.join(sources)}" 
                               for directive, sources in csp_directives.items()])
        
        response.headers['Content-Security-Policy'] = csp_header
        
        # Report-Only CSP for testing new policies
        if env != 'production':
            test_csp = self._build_test_csp_directives()
            if test_csp:
                test_csp_header = '; '.join([f"{directive} {' '.join(sources)}" 
                                           for directive, sources in test_csp.items()])
                response.headers['Content-Security-Policy-Report-Only'] = test_csp_header
        
        # Feature Policy / Permissions Policy
        permissions_policy = self._build_permissions_policy()
        response.headers['Permissions-Policy'] = permissions_policy
    
    def _build_csp_directives(self, env: str) -> Dict[str, List[str]]:
        """Build Content Security Policy directives"""
        
        if env == 'production':
            return {
                'default-src': ["'self'"],
                'script-src': [
                    "'self'",
                    "'unsafe-inline'",  # Consider removing and using nonces
                    'https://cdnjs.cloudflare.com',
                    'https://cdn.jsdelivr.net'
                ],
                'style-src': [
                    "'self'",
                    "'unsafe-inline'",  # For CSS-in-JS libraries
                    'https://fonts.googleapis.com'
                ],
                'img-src': [
                    "'self'",
                    'data:',
                    'https:',
                    'blob:'
                ],
                'font-src': [
                    "'self'",
                    'https://fonts.gstatic.com'
                ],
                'connect-src': [
                    "'self'",
                    'wss:',
                    'https:'
                ],
                'media-src': ["'self'"],
                'object-src': ["'none'"],
                'frame-src': ["'none'"],
                'frame-ancestors': ["'none'"],
                'form-action': ["'self'"],
                'base-uri': ["'self'"],
                'manifest-src': ["'self'"],
                'worker-src': ["'self'"],
                'report-uri': ['/csp-report'],
                'upgrade-insecure-requests': []
            }
        else:
            # Development CSP - more permissive
            return {
                'default-src': ["'self'"],
                'script-src': [
                    "'self'",
                    "'unsafe-inline'",
                    "'unsafe-eval'",  # For development tools
                    'localhost:*',
                    '127.0.0.1:*'
                ],
                'style-src': [
                    "'self'",
                    "'unsafe-inline'",
                    'localhost:*',
                    '127.0.0.1:*'
                ],
                'img-src': [
                    "'self'",
                    'data:',
                    'blob:',
                    'localhost:*',
                    '127.0.0.1:*'
                ],
                'font-src': [
                    "'self'",
                    'data:',
                    'localhost:*',
                    '127.0.0.1:*'
                ],
                'connect-src': [
                    "'self'",
                    'ws:',
                    'wss:',
                    'localhost:*',
                    '127.0.0.1:*'
                ],
                'frame-ancestors': ["'none'"],
                'object-src': ["'none'"],
                'base-uri': ["'self'"]
            }
    
    def _build_test_csp_directives(self) -> Optional[Dict[str, List[str]]]:
        """Build test CSP directives for report-only mode"""
        
        # Example of a stricter CSP for testing
        return {
            'default-src': ["'self'"],
            'script-src': ["'self'"],
            'style-src': ["'self'"],
            'img-src': ["'self'", 'data:'],
            'report-uri': ['/csp-report-test']
        }
    
    def _build_permissions_policy(self) -> str:
        """Build Permissions Policy header"""
        
        policies = [
            'geolocation=()',
            'microphone=()',
            'camera=()',
            'fullscreen=(self)',
            'payment=()',
            'usb=()',
            'magnetometer=()',
            'accelerometer=()',
            'gyroscope=()',
            'midi=()',
            'sync-xhr=()',
            'clipboard-read=()',
            'clipboard-write=(self)',
            'web-share=(self)'
        ]
        
        return ', '.join(policies)
    
    def _add_privacy_headers(self, response):
        """Add privacy-related headers"""
        
        # Clear-Site-Data: Clear browser data when needed
        # (This should be used selectively, e.g., on logout)
        if request.endpoint in ['auth.logout', 'auth.delete_account']:
            response.headers['Clear-Site-Data'] = '"cache", "cookies", "storage"'
        
        # Cross-Origin-Embedder-Policy: Control embedding
        response.headers['Cross-Origin-Embedder-Policy'] = 'require-corp'
        
        # Cross-Origin-Opener-Policy: Isolate browsing context
        response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
        
        # Cross-Origin-Resource-Policy: Control resource access
        response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'
    
    def _add_performance_headers(self, response):
        """Add performance and caching related headers"""
        
        # Cache-Control for different content types
        if request.endpoint in ['static', 'api.leaderboard']:
            # Static files and some API endpoints can be cached
            response.headers['Cache-Control'] = 'public, max-age=3600'
        elif request.path.startswith('/api/'):
            # API responses shouldn't be cached by default
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        
        # Vary header for proper caching
        vary_headers = []
        if 'Origin' in request.headers:
            vary_headers.append('Origin')
        if 'Accept-Encoding' in request.headers:
            vary_headers.append('Accept-Encoding')
        if 'User-Agent' in request.headers:
            vary_headers.append('User-Agent')
        
        if vary_headers:
            response.headers['Vary'] = ', '.join(vary_headers)
    
    def _add_custom_headers(self, response):
        """Add any custom headers"""
        
        # Application identification (be careful not to expose too much)
        response.headers['X-App-Name'] = 'CS-Gauntlet'
        response.headers['X-App-Version'] = current_app.config.get('VERSION', '1.0.0')
        
        # Request ID for tracing
        if hasattr(g, 'request_id'):
            response.headers['X-Request-ID'] = g.request_id
        
        # Rate limiting information
        if hasattr(g, 'rate_limit_remaining'):
            response.headers['X-RateLimit-Remaining'] = str(g.rate_limit_remaining)
        if hasattr(g, 'rate_limit_reset'):
            response.headers['X-RateLimit-Reset'] = str(g.rate_limit_reset)
        
        # Response time
        if hasattr(g, 'request_start_time'):
            response_time = int((time.time() - g.request_start_time) * 1000)
            response.headers['X-Response-Time'] = f"{response_time}ms"
        
        # Add custom headers from configuration
        for name, value in self.custom_headers.items():
            response.headers[name] = value
    
    def _add_conditional_headers(self, response):
        """Add headers based on conditions"""
        
        for condition, headers in self.conditional_headers.items():
            if condition():
                for name, value in headers.items():
                    response.headers[name] = value
    
    def _log_headers_applied(self, response):
        """Log which security headers were applied"""
        
        security_header_names = [
            'Content-Security-Policy',
            'Strict-Transport-Security',
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
            'Referrer-Policy',
            'Permissions-Policy'
        ]
        
        applied_headers = {
            name: response.headers.get(name, 'Not Set')
            for name in security_header_names
        }
        
        SecurityAudit.log_security_event(
            'security_headers_applied',
            details={
                'endpoint': request.endpoint,
                'headers': applied_headers
            }
        )
    
    def add_custom_header(self, name: str, value: str):
        """Add a custom header to all responses"""
        self.custom_headers[name] = value
    
    def add_conditional_header(self, condition: Callable[[], bool], headers: Dict[str, str]):
        """Add headers based on a condition function"""
        self.conditional_headers[condition] = headers
    
    def remove_server_headers(self, response):
        """Remove server identification headers"""
        headers_to_remove = ['Server', 'X-Powered-By', 'Via']
        for header in headers_to_remove:
            response.headers.pop(header, None)
        return response

class CSPReporter:
    """Handle Content Security Policy violation reports"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize CSP reporting"""
        
        @app.route('/csp-report', methods=['POST'])
        def csp_report():
            """Handle CSP violation reports"""
            try:
                report_data = request.get_json()
                
                SecurityAudit.log_security_event(
                    'csp_violation_report',
                    details={
                        'report': report_data,
                        'user_agent': request.headers.get('User-Agent'),
                        'ip_address': request.remote_addr
                    }
                )
                
                # In production, you might want to send this to a monitoring service
                # like Sentry, DataDog, or a custom analytics endpoint
                
                return '', 204
                
            except Exception as e:
                current_app.logger.error(f"Error processing CSP report: {e}")
                return '', 400
        
        @app.route('/csp-report-test', methods=['POST'])
        def csp_report_test():
            """Handle test CSP violation reports"""
            try:
                report_data = request.get_json()
                
                SecurityAudit.log_security_event(
                    'csp_test_violation_report',
                    details={
                        'report': report_data,
                        'user_agent': request.headers.get('User-Agent')
                    }
                )
                
                return '', 204
                
            except Exception as e:
                current_app.logger.error(f"Error processing test CSP report: {e}")
                return '', 400

class SecurityHeadersConfig:
    """Configuration class for security headers"""
    
    PRODUCTION_CONFIG = {
        'csp_strict': True,
        'hsts_max_age': 31536000,  # 1 year
        'hsts_include_subdomains': True,
        'hsts_preload': True,
        'expect_ct': True,
        'referrer_policy': 'strict-origin-when-cross-origin'
    }
    
    DEVELOPMENT_CONFIG = {
        'csp_strict': False,
        'hsts_max_age': 3600,  # 1 hour
        'hsts_include_subdomains': False,
        'hsts_preload': False,
        'expect_ct': False,
        'referrer_policy': 'no-referrer-when-downgrade'
    }
    
    @classmethod
    def get_config(cls, env: str) -> Dict:
        """Get configuration for environment"""
        if env == 'production':
            return cls.PRODUCTION_CONFIG.copy()
        else:
            return cls.DEVELOPMENT_CONFIG.copy()

def setup_security_headers(app):
    """Setup comprehensive security headers"""
    
    # Main security headers middleware
    security_headers = SecurityHeaders(app)
    
    # CSP reporter
    csp_reporter = CSPReporter(app)
    
    # Add environment-specific custom headers
    env = app.config.get('ENV', 'development')
    if env != 'production':
        security_headers.add_custom_header('X-Debug-Mode', 'enabled')
    
    # Add conditional headers
    def is_api_request():
        return request.path.startswith('/api/')
    
    security_headers.add_conditional_header(
        is_api_request,
        {'X-API-Version': 'v1'}
    )
    
    # Remove server headers in production
    if env == 'production':
        app.after_request(security_headers.remove_server_headers)
    
    return {
        'headers': security_headers,
        'csp_reporter': csp_reporter
    }

# Security header validation functions
def validate_csp_policy(policy: str) -> bool:
    """Validate CSP policy syntax"""
    try:
        # Basic validation - check for common CSP directive format
        directives = policy.split(';')
        for directive in directives:
            directive = directive.strip()
            if directive and ' ' in directive:
                directive_name = directive.split(' ')[0]
                if not directive_name.replace('-', '').isalpha():
                    return False
        return True
    except Exception:
        return False

def check_header_security(headers: Dict[str, str]) -> List[str]:
    """Check headers for security issues"""
    issues = []
    
    # Check for missing security headers
    required_headers = [
        'X-Content-Type-Options',
        'X-Frame-Options',
        'Content-Security-Policy'
    ]
    
    for header in required_headers:
        if header not in headers:
            issues.append(f"Missing required security header: {header}")
    
    # Check for insecure configurations
    if headers.get('X-Frame-Options') == 'ALLOWALL':
        issues.append("X-Frame-Options set to ALLOWALL (insecure)")
    
    if 'unsafe-eval' in headers.get('Content-Security-Policy', ''):
        issues.append("CSP allows unsafe-eval (potentially insecure)")
    
    return issues