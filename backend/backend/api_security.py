"""
API Authentication and Security for CS Gauntlet
Provides comprehensive API security including JWT, API keys, scoping, and rate limiting
"""

import jwt
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from functools import wraps
from flask import Blueprint, request, jsonify, current_app, g
from flask_login import current_user
import re

from .models import User, db
from .security import SecurityValidator, SecurityAudit
from .audit_logger import AuditEventType, AuditSeverity
from .session_security import SessionManager
from .rate_limiting import AdvancedRateLimiter

api_security = Blueprint('api_security', __name__, url_prefix='/api/v1')

class APIKeyManager:
    """Manages API keys for programmatic access"""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.key_prefix = "api_key:"
        self.usage_prefix = "api_usage:"
        
        # API key scopes and permissions
        self.scopes = {
            'read': ['get_profile', 'get_problems', 'get_leaderboard', 'get_submissions'],
            'write': ['submit_solution', 'update_profile', 'create_game'],
            'admin': ['manage_users', 'manage_problems', 'view_analytics'],
            'game': ['join_game', 'submit_solution', 'get_game_state'],
            'submissions': ['submit_solution', 'get_submissions', 'get_results']
        }
    
    def generate_api_key(self, user_id: int, name: str, scopes: List[str], 
                        expires_in_days: int = 30) -> Tuple[str, str]:
        """Generate new API key for user"""
        
        # Generate key components
        key_id = secrets.token_hex(8)
        key_secret = secrets.token_urlsafe(32)
        api_key = f"cgk_{key_id}.{key_secret}"  # CS Gauntlet Key format
        
        # Create key metadata
        key_data = {
            'user_id': user_id,
            'key_id': key_id,
            'name': name,
            'scopes': scopes,
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(days=expires_in_days)).isoformat(),
            'active': True,
            'usage_count': 0,
            'last_used_at': None,
            'last_used_ip': None
        }
        
        # Hash the secret for storage
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Store in Redis
        if self.redis_client:
            self.redis_client.setex(
                f"{self.key_prefix}{key_hash}",
                86400 * expires_in_days,
                json.dumps(key_data)
            )
            
            # Add to user's keys
            user_keys_key = f"user_api_keys:{user_id}"
            self.redis_client.sadd(user_keys_key, key_hash)
            self.redis_client.expire(user_keys_key, 86400 * expires_in_days)
        
        # Log API key creation
        SecurityAudit.log_security_event(
            event_type=AuditEventType.API_KEY_CREATED,
            severity=AuditSeverity.MEDIUM,
            success=True,
            message="API key created",
            details={
                'key_id': key_id,
                'scopes': scopes,
                'expires_in_days': expires_in_days
            },
            user_id=str(user_id)
        )
        
        return api_key, key_id
    
    def validate_api_key(self, api_key: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Validate API key and return key data"""
        
        try:
            # Parse API key format
            if not api_key.startswith('cgk_'):
                return False, None, "Invalid API key format"
            
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            # Get key data from Redis
            if self.redis_client:
                key_data_json = self.redis_client.get(f"{self.key_prefix}{key_hash}")
                
                if not key_data_json:
                    return False, None, "API key not found or expired"
                
                key_data = json.loads(key_data_json)
                
                # Check if key is active
                if not key_data.get('active', False):
                    return False, None, "API key deactivated"
                
                # Check expiration
                expires_at = datetime.fromisoformat(key_data['expires_at'])
                if datetime.utcnow() > expires_at:
                    return False, None, "API key expired"
                
                # Update usage
                key_data['usage_count'] = key_data.get('usage_count', 0) + 1
                key_data['last_used_at'] = datetime.utcnow().isoformat()
                key_data['last_used_ip'] = request.remote_addr if request else None
                
                # Store updated data
                self.redis_client.setex(
                    f"{self.key_prefix}{key_hash}",
                    int((expires_at - datetime.utcnow()).total_seconds()),
                    json.dumps(key_data)
                )
                
                return True, key_data, None
            
            else:
                return False, None, "API key validation service unavailable"
                
        except Exception as e:
            current_app.logger.error(f"API key validation error: {e}")
            return False, None, "API key validation failed"
    
    def revoke_api_key(self, key_id: str, user_id: int) -> bool:
        """Revoke an API key"""
        
        try:
            if self.redis_client:
                # Find key by key_id
                user_keys_key = f"user_api_keys:{user_id}"
                user_key_hashes = self.redis_client.smembers(user_keys_key)
                
                for key_hash in user_key_hashes:
                    key_data_json = self.redis_client.get(f"{self.key_prefix}{key_hash.decode()}")
                    if key_data_json:
                        key_data = json.loads(key_data_json)
                        if key_data.get('key_id') == key_id:
                            # Deactivate key
                            key_data['active'] = False
                            key_data['revoked_at'] = datetime.utcnow().isoformat()
                            
                            self.redis_client.setex(
                                f"{self.key_prefix}{key_hash.decode()}",
                                3600,  # Keep for 1 hour for audit
                                json.dumps(key_data)
                            )
                            
                            # Remove from user's active keys
                            self.redis_client.srem(user_keys_key, key_hash)
                            
                            # Log revocation
                            SecurityAudit.log_security_event(
                                event_type=AuditEventType.API_KEY_REVOKED,
                                severity=AuditSeverity.MEDIUM,
                                success=True,
                                message="API key revoked",
                                details={'key_id': key_id},
                                user_id=str(user_id)
                            )
                            
                            return True
            
            return False
            
        except Exception as e:
            current_app.logger.error(f"API key revocation error: {e}")
            return False
    
    def get_user_api_keys(self, user_id: int) -> List[Dict]:
        """Get all API keys for a user"""
        
        try:
            if not self.redis_client:
                return []
            
            user_keys_key = f"user_api_keys:{user_id}"
            user_key_hashes = self.redis_client.smembers(user_keys_key)
            
            keys = []
            for key_hash in user_key_hashes:
                key_data_json = self.redis_client.get(f"{self.key_prefix}{key_hash.decode()}")
                if key_data_json:
                    key_data = json.loads(key_data_json)
                    
                    # Return safe subset of data
                    keys.append({
                        'key_id': key_data.get('key_id'),
                        'name': key_data.get('name'),
                        'scopes': key_data.get('scopes', []),
                        'created_at': key_data.get('created_at'),
                        'expires_at': key_data.get('expires_at'),
                        'usage_count': key_data.get('usage_count', 0),
                        'last_used_at': key_data.get('last_used_at'),
                        'active': key_data.get('active', False)
                    })
            
            return keys
            
        except Exception as e:
            current_app.logger.error(f"Get user API keys error: {e}")
            return []
    
    def check_scope_permission(self, user_scopes: List[str], required_scope: str) -> bool:
        """Check if user has required scope permission"""
        
        if 'admin' in user_scopes:
            return True  # Admin has all permissions
        
        for scope in user_scopes:
            if scope in self.scopes:
                if required_scope in self.scopes[scope]:
                    return True
        
        return False

class JWTManager:
    """Enhanced JWT management for API access"""
    
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or current_app.config.get('JWT_SECRET_KEY')
        self.algorithm = 'HS256'
        self.issuer = 'cs-gauntlet-api'
        
        # Token types and their properties
        self.token_types = {
            'access': {'lifetime': 3600, 'scope': 'api_access'},      # 1 hour
            'refresh': {'lifetime': 86400 * 7, 'scope': 'token_refresh'}, # 1 week
            'api': {'lifetime': 86400 * 30, 'scope': 'api_long_term'}     # 30 days
        }
    
    def create_token(self, user_id: int, token_type: str = 'access', 
                    scopes: List[str] = None, additional_claims: Dict = None) -> str:
        """Create JWT token"""
        
        if token_type not in self.token_types:
            raise ValueError(f"Invalid token type: {token_type}")
        
        now = datetime.utcnow()
        token_config = self.token_types[token_type]
        
        payload = {
            'user_id': user_id,
            'token_type': token_type,
            'scopes': scopes or [],
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(seconds=token_config['lifetime'])).timestamp()),
            'iss': self.issuer,
            'aud': 'cs-gauntlet-client',
            'jti': secrets.token_hex(16)  # Unique token ID
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def validate_token(self, token: str, required_scopes: List[str] = None) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Validate JWT token"""
        
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience='cs-gauntlet-client',
                issuer=self.issuer
            )
            
            # Check token type
            token_type = payload.get('token_type', 'access')
            if token_type not in self.token_types:
                return False, None, "Invalid token type"
            
            # Check scopes if required
            if required_scopes:
                token_scopes = payload.get('scopes', [])
                if not any(scope in token_scopes for scope in required_scopes):
                    return False, None, "Insufficient scope permissions"
            
            return True, payload, None
            
        except jwt.ExpiredSignatureError:
            return False, None, "Token expired"
        except jwt.InvalidTokenError as e:
            return False, None, f"Invalid token: {str(e)}"
        except Exception as e:
            return False, None, f"Token validation error: {str(e)}"

# Authentication decorators

def require_api_auth(scopes: List[str] = None, allow_session: bool = True):
    """Decorator to require API authentication"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Try API key authentication first
            api_key = request.headers.get('X-API-Key')
            if api_key:
                api_key_manager = getattr(g, 'api_key_manager', None)
                if api_key_manager:
                    is_valid, key_data, error = api_key_manager.validate_api_key(api_key)
                    
                    if is_valid:
                        # Check scope permissions
                        if scopes:
                            user_scopes = key_data.get('scopes', [])
                            has_permission = any(
                                api_key_manager.check_scope_permission(user_scopes, scope)
                                for scope in scopes
                            )
                            
                            if not has_permission:
                                return jsonify({'error': 'Insufficient API permissions'}), 403
                        
                        # Set user context
                        g.api_user_id = key_data['user_id']
                        g.api_auth_method = 'api_key'
                        g.api_scopes = key_data.get('scopes', [])
                        
                        return f(*args, **kwargs)
                    
                    else:
                        return jsonify({'error': f'Invalid API key: {error}'}), 401
            
            # Try JWT authentication
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header[7:]
                jwt_manager = getattr(g, 'jwt_manager', None)
                
                if jwt_manager:
                    is_valid, payload, error = jwt_manager.validate_token(token, scopes)
                    
                    if is_valid:
                        g.api_user_id = payload['user_id']
                        g.api_auth_method = 'jwt'
                        g.api_scopes = payload.get('scopes', [])
                        
                        return f(*args, **kwargs)
                    
                    else:
                        return jsonify({'error': f'Invalid token: {error}'}), 401
            
            # Try session authentication if allowed
            if allow_session and current_user.is_authenticated:
                g.api_user_id = current_user.id
                g.api_auth_method = 'session'
                g.api_scopes = ['read', 'write']  # Default scopes for session auth
                
                return f(*args, **kwargs)
            
            return jsonify({'error': 'Authentication required'}), 401
        
        return decorated_function
    return decorator

def require_scope(scope: str):
    """Decorator to require specific API scope"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_scopes = getattr(g, 'api_scopes', [])
            
            # Check if user has required scope
            api_key_manager = getattr(g, 'api_key_manager', None)
            if api_key_manager and not api_key_manager.check_scope_permission(user_scopes, scope):
                return jsonify({'error': f'Scope {scope} required'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def api_rate_limit(requests_per_minute: int = 60):
    """Decorator for API-specific rate limiting"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            rate_limiter = getattr(g, 'rate_limiter', None)
            if rate_limiter:
                # Use different rate limiting based on auth method
                auth_method = getattr(g, 'api_auth_method', 'anonymous')
                user_id = getattr(g, 'api_user_id', None)
                
                if auth_method == 'api_key':
                    rate_key = f"api_rate:{user_id}:{f.__name__}"
                    limit = requests_per_minute * 2  # Higher limit for API keys
                elif auth_method == 'jwt':
                    rate_key = f"jwt_rate:{user_id}:{f.__name__}"
                    limit = requests_per_minute
                else:
                    rate_key = f"session_rate:{request.remote_addr}:{f.__name__}"
                    limit = requests_per_minute // 2  # Lower limit for session auth
                
                if not rate_limiter.is_allowed(rate_key, limit, 60):
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'retry_after': 60,
                        'limit': limit
                    }), 429
                
                rate_limiter.record_request(rate_key)
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

# API endpoints for key management

@api_security.route('/auth/api-keys', methods=['POST'])
@require_api_auth(allow_session=True)
def create_api_key():
    """Create new API key"""
    
    try:
        data = request.get_json()
        
        name = data.get('name', '').strip()
        scopes = data.get('scopes', [])
        expires_in_days = data.get('expires_in_days', 30)
        
        # Validate input
        if not name or len(name) < 3:
            return jsonify({'error': 'Key name must be at least 3 characters'}), 400
        
        if not isinstance(scopes, list) or not scopes:
            return jsonify({'error': 'At least one scope is required'}), 400
        
        # Validate scopes
        api_key_manager = getattr(g, 'api_key_manager')
        valid_scopes = list(api_key_manager.scopes.keys())
        
        for scope in scopes:
            if scope not in valid_scopes:
                return jsonify({'error': f'Invalid scope: {scope}'}), 400
        
        # Validate expiry
        if not isinstance(expires_in_days, int) or expires_in_days < 1 or expires_in_days > 365:
            return jsonify({'error': 'Expires in days must be between 1 and 365'}), 400
        
        # Create API key
        user_id = getattr(g, 'api_user_id')
        api_key, key_id = api_key_manager.generate_api_key(
            user_id, name, scopes, expires_in_days
        )
        
        return jsonify({
            'success': True,
            'api_key': api_key,
            'key_id': key_id,
            'message': 'API key created successfully. Store this key securely - it will not be shown again.'
        })
        
    except Exception as e:
        current_app.logger.error(f"API key creation error: {e}")
        return jsonify({'error': 'Failed to create API key'}), 500

@api_security.route('/auth/api-keys', methods=['GET'])
@require_api_auth(allow_session=True)
def list_api_keys():
    """List user's API keys"""
    
    try:
        user_id = getattr(g, 'api_user_id')
        api_key_manager = getattr(g, 'api_key_manager')
        
        keys = api_key_manager.get_user_api_keys(user_id)
        
        return jsonify({
            'success': True,
            'api_keys': keys
        })
        
    except Exception as e:
        current_app.logger.error(f"List API keys error: {e}")
        return jsonify({'error': 'Failed to list API keys'}), 500

@api_security.route('/auth/api-keys/<key_id>', methods=['DELETE'])
@require_api_auth(allow_session=True)
def revoke_api_key(key_id):
    """Revoke an API key"""
    
    try:
        user_id = getattr(g, 'api_user_id')
        api_key_manager = getattr(g, 'api_key_manager')
        
        success = api_key_manager.revoke_api_key(key_id, user_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'API key revoked successfully'
            })
        else:
            return jsonify({'error': 'API key not found or already revoked'}), 404
            
    except Exception as e:
        current_app.logger.error(f"API key revocation error: {e}")
        return jsonify({'error': 'Failed to revoke API key'}), 500

@api_security.route('/auth/token', methods=['POST'])
@require_api_auth(allow_session=True)
def create_jwt_token():
    """Create JWT token for API access"""
    
    try:
        data = request.get_json()
        
        token_type = data.get('type', 'access')
        scopes = data.get('scopes', ['read'])
        
        user_id = getattr(g, 'api_user_id')
        jwt_manager = getattr(g, 'jwt_manager')
        
        token = jwt_manager.create_token(user_id, token_type, scopes)
        
        return jsonify({
            'success': True,
            'token': token,
            'type': token_type,
            'scopes': scopes
        })
        
    except Exception as e:
        current_app.logger.error(f"JWT token creation error: {e}")
        return jsonify({'error': 'Failed to create token'}), 500

# Initialize API security

def init_api_security(app, redis_client=None):
    """Initialize API security components"""
    
    try:
        # Create managers
        api_key_manager = APIKeyManager(redis_client)
        jwt_manager = JWTManager()
        
        @app.before_request
        def before_request_api():
            """Set up API security for each request"""
            g.api_key_manager = api_key_manager
            g.jwt_manager = jwt_manager
        
        app.logger.info("API security initialized successfully")
        
        return {
            'api_key_manager': api_key_manager,
            'jwt_manager': jwt_manager
        }
        
    except Exception as e:
        app.logger.error(f"API security initialization failed: {e}")
        return None

# Register API security blueprint
def register_api_security(app):
    """Register API security blueprint and initialize components"""
    
    app.register_blueprint(api_security)
    
    try:
        from . import redis_client
        api_components = init_api_security(app, redis_client)
        
        if api_components:
            app.logger.info("API authentication and security initialized")
            return api_components
        else:
            app.logger.warning("API security initialization failed")
            return None
            
    except Exception as e:
        app.logger.warning(f"API security setup failed: {e}")
        return None

import json