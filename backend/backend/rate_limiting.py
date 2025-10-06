from flask import request, jsonify, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
import time
import json
from datetime import datetime, timedelta
from .security import SecurityAudit

class RateLimitConfig:
    """Rate limiting configuration for different endpoints"""
    
    # Rate limits for different types of operations
    LIMITS = {
        'auth': {
            'login': "5 per minute",
            'register': "3 per minute", 
            'password_reset': "2 per minute"
        },
        'api': {
            'general': "100 per minute",
            'code_submission': "10 per minute",
            'file_upload': "5 per minute",
            'leaderboard': "30 per minute"
        },
        'game': {
            'join_game': "20 per minute",
            'submit_solution': "15 per minute",
            'create_game': "5 per minute"
        },
        'admin': {
            'general': "200 per minute"
        }
    }
    
    # Stricter limits for suspicious IPs
    SUSPICIOUS_LIMITS = {
        'general': "20 per minute",
        'auth': "2 per minute"
    }

def init_rate_limiting(app, redis_client=None):
    """Initialize rate limiting for the application"""
    
    try:
        # Create advanced rate limiter
        rate_limiter = AdvancedRateLimiter(redis_client)
        
        @app.before_request
        def before_request_rate_limit():
            """Apply rate limiting before each request"""
            from flask import g
            g.rate_limiter = rate_limiter
        
        app.logger.info("Rate limiting initialized successfully")
        return rate_limiter
        
    except Exception as e:
        app.logger.error(f"Rate limiting initialization failed: {e}")
        return None

def create_limiter(app):
    """Create and configure Flask-Limiter"""
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["1000 per hour", "100 per minute"],
        storage_uri="redis://localhost:6379",  # Use Redis for distributed rate limiting
        strategy="fixed-window"
    )
    
    # Custom error handler for rate limit exceeded
    @limiter.request_filter
    def filter_requests():
        """Filter requests that should be exempt from rate limiting"""
        # Exempt health checks and static files
        if request.endpoint in ['health', 'static']:
            return True
        return False
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        """Custom rate limit exceeded handler"""
        SecurityAudit.log_security_event(
            'rate_limit_exceeded',
            user_id=getattr(request, 'current_user', {}).get('id'),
            details={
                'endpoint': request.endpoint,
                'method': request.method,
                'limit': str(e.limit),
                'retry_after': e.retry_after
            }
        )
        
        return jsonify({
            'error': 'Rate limit exceeded',
            'message': f'Too many requests. Try again in {e.retry_after} seconds.',
            'retry_after': e.retry_after
        }), 429
    
    return limiter

def adaptive_rate_limit(base_limit, suspicious_multiplier=0.2):
    """Decorator for adaptive rate limiting based on user behavior"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = get_remote_address()
            
            # Check if IP is flagged as suspicious
            if is_suspicious_ip(client_ip):
                # Apply stricter limits
                current_limit = apply_multiplier(base_limit, suspicious_multiplier)
                SecurityAudit.log_security_event(
                    'suspicious_ip_rate_limited',
                    ip_address=client_ip,
                    details={'original_limit': base_limit, 'applied_limit': current_limit}
                )
            else:
                current_limit = base_limit
            
            # Apply the rate limit
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def is_suspicious_ip(ip_address):
    """Check if an IP address exhibits suspicious behavior"""
    # This could be enhanced with Redis/database tracking
    # For now, implement basic checks
    
    # Check against known bad IP lists (implement as needed)
    # Check recent failed authentication attempts
    # Check for unusual request patterns
    
    return False  # Placeholder implementation

def apply_multiplier(limit_string, multiplier):
    """Apply a multiplier to a rate limit string"""
    parts = limit_string.split(' per ')
    if len(parts) == 2:
        count = int(parts[0])
        period = parts[1]
        new_count = max(1, int(count * multiplier))
        return f"{new_count} per {period}"
    return limit_string

class AdvancedRateLimiter:
    """Advanced rate limiting with custom logic"""
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.window_size = 60  # 60 seconds
    
    def is_allowed(self, key, limit, window=None):
        """Check if request is allowed under the rate limit"""
        if not self.redis:
            return True  # Fallback when Redis is not available
        
        window = window or self.window_size
        now = int(time.time())
        window_start = now - window
        
        # Use sliding window log algorithm
        pipe = self.redis.pipeline()
        
        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current requests in window
        pipe.zcard(key)
        
        # Add current request
        pipe.zadd(key, {str(now): now})
        
        # Set expiration
        pipe.expire(key, window + 1)
        
        results = pipe.execute()
        request_count = results[1]
        
        return request_count < limit
    
    def record_request(self, key):
        """Record a request for rate limiting purposes"""
        if not self.redis:
            return
        
        now = int(time.time())
        self.redis.zadd(key, {str(now): now})

def rate_limit_by_user(limit_per_minute=60):
    """Rate limit decorator based on authenticated user"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = None
            
            # Try to get user ID from different auth methods
            if hasattr(request, 'current_user') and request.current_user:
                user_id = request.current_user.id
            elif hasattr(request, 'user_id'):
                user_id = request.user_id
            
            if user_id:
                limiter_key = f"user_rate_limit:{user_id}"
                
                # Use advanced rate limiter if available
                if hasattr(current_app, 'advanced_limiter'):
                    if not current_app.advanced_limiter.is_allowed(limiter_key, limit_per_minute):
                        SecurityAudit.log_security_event(
                            'user_rate_limit_exceeded',
                            user_id=user_id,
                            details={'limit': limit_per_minute, 'endpoint': request.endpoint}
                        )
                        return jsonify({
                            'error': 'Rate limit exceeded',
                            'message': f'Maximum {limit_per_minute} requests per minute allowed'
                        }), 429
                    
                    current_app.advanced_limiter.record_request(limiter_key)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def rate_limit_by_endpoint(limits_dict):
    """Rate limit decorator with different limits per endpoint"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            endpoint = request.endpoint
            method = request.method.lower()
            
            # Get limit for this endpoint and method
            limit_key = f"{endpoint}_{method}"
            limit = limits_dict.get(limit_key, limits_dict.get(endpoint, "60 per minute"))
            
            client_ip = get_remote_address()
            rate_limit_key = f"endpoint_rate_limit:{client_ip}:{limit_key}"
            
            # Parse limit string (e.g., "10 per minute")
            parts = limit.split(' per ')
            if len(parts) == 2:
                count = int(parts[0])
                period = parts[1]
                
                if period == "minute":
                    window = 60
                elif period == "hour":
                    window = 3600
                elif period == "day":
                    window = 86400
                else:
                    window = 60
                
                # Check rate limit
                if hasattr(current_app, 'advanced_limiter'):
                    if not current_app.advanced_limiter.is_allowed(rate_limit_key, count, window):
                        SecurityAudit.log_security_event(
                            'endpoint_rate_limit_exceeded',
                            ip_address=client_ip,
                            details={
                                'endpoint': endpoint,
                                'method': method,
                                'limit': limit
                            }
                        )
                        return jsonify({
                            'error': 'Rate limit exceeded',
                            'message': f'Maximum {limit} allowed for this endpoint'
                        }), 429
                    
                    current_app.advanced_limiter.record_request(rate_limit_key)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Predefined rate limiters for common use cases
auth_rate_limit = rate_limit_by_endpoint({
    'auth.login': "5 per minute",
    'auth.register': "3 per minute",
    'auth.forgot_password': "2 per minute",
    'auth.reset_password': "3 per minute"
})

api_rate_limit = rate_limit_by_endpoint({
    'main.api_profile': "30 per minute",
    'main.api_leaderboard': "30 per minute",
    'main.submit_code_with_ai_grading': "10 per minute",
    'main.compare_solutions': "5 per minute",
    'main.upload_avatar': "3 per minute"
})

game_rate_limit = rate_limit_by_endpoint({
    'main.create_custom_game': "5 per minute",
    'main.join_custom_game': "20 per minute",
    'socketio.start_game': "10 per minute",
    'socketio.submit_solution': "15 per minute"
})

# Burst protection for code execution
code_execution_rate_limit = rate_limit_by_user(10)  # 10 code executions per minute per user

# File upload limits
file_upload_rate_limit = rate_limit_by_endpoint({
    'main.upload_avatar': "3 per minute",
    'main.update_profile': "5 per minute"
})

def setup_rate_limiting(app, redis_client=None):
    """Setup rate limiting for the Flask app"""
    # Create standard limiter
    limiter = create_limiter(app)
    
    # Create advanced limiter if Redis is available
    if redis_client:
        app.advanced_limiter = AdvancedRateLimiter(redis_client)
    
    return limiter