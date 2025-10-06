"""
Secure Session Management for CS Gauntlet
Handles JWT tokens, session validation, and secure authentication state
"""

import jwt
import redis
import time
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple, Any
from flask import current_app, request, g
from flask_login import current_user
from functools import wraps
import json

from .security import SecurityValidator
from .audit_logger import AuditEventType, AuditSeverity
from .models import User

class SessionManager:
    """Manages secure user sessions with JWT and Redis"""
    
    def __init__(self, redis_client=None, jwt_secret_key=None):
        self.redis_client = redis_client
        self.jwt_secret_key = jwt_secret_key or secrets.token_urlsafe(32)
        self.algorithm = 'HS256'
        
        # Session configuration
        self.session_timeout = 3600 * 24  # 24 hours
        self.refresh_threshold = 3600 * 6  # Refresh if expires within 6 hours
        self.max_sessions_per_user = 5
        
        # Security settings
        self.require_https = current_app.config.get('ENV') == 'production'
        self.secure_cookies = current_app.config.get('ENV') == 'production'
        
    def create_session(self, user_id: int, username: str, 
                      additional_claims: Dict = None) -> Tuple[str, str, Dict]:
        """Create a new secure session for user"""
        
        # Generate session ID
        session_id = self._generate_session_id()
        
        # Prepare JWT payload
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=self.session_timeout)
        
        payload = {
            'user_id': user_id,
            'username': username,
            'session_id': session_id,
            'iat': int(now.timestamp()),
            'exp': int(expires_at.timestamp()),
            'iss': 'cs-gauntlet',
            'aud': 'cs-gauntlet-client',
            'jti': session_id  # JWT ID for tracking
        }
        
        # Add additional claims
        if additional_claims:
            payload.update(additional_claims)
        
        # Generate JWT token
        access_token = jwt.encode(payload, self.jwt_secret_key, algorithm=self.algorithm)
        
        # Generate refresh token
        refresh_payload = {
            'user_id': user_id,
            'session_id': session_id,
            'type': 'refresh',
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(days=30)).timestamp())  # 30 days
        }
        refresh_token = jwt.encode(refresh_payload, self.jwt_secret_key, algorithm=self.algorithm)
        
        # Store session in Redis
        session_data = {
            'user_id': user_id,
            'username': username,
            'created_at': now.isoformat(),
            'last_activity': now.isoformat(),
            'ip_address': request.remote_addr if request else None,
            'user_agent': request.headers.get('User-Agent', '')[:200] if request else None,
            'active': True,
            'access_token_hash': hashlib.sha256(access_token.encode()).hexdigest(),
            'refresh_token_hash': hashlib.sha256(refresh_token.encode()).hexdigest()
        }
        
        if additional_claims:
            session_data['additional_claims'] = additional_claims
        
        if self.redis_client:
            # Store session data
            session_key = f"session:{session_id}"
            self.redis_client.setex(
                session_key, 
                self.session_timeout, 
                json.dumps(session_data)
            )
            
            # Track user sessions
            user_sessions_key = f"user_sessions:{user_id}"
            self.redis_client.sadd(user_sessions_key, session_id)
            self.redis_client.expire(user_sessions_key, self.session_timeout)
            
            # Cleanup old sessions if too many
            self._cleanup_user_sessions(user_id)
        
        # Log session creation
        from .security import SecurityAudit
        SecurityAudit.log_security_event(
            event_type=AuditEventType.LOGIN_SUCCESS,
            severity=AuditSeverity.LOW,
            success=True,
            message="Secure session created",
            details={
                'session_id': session_id,
                'expires_at': expires_at.isoformat(),
                'user_agent': session_data.get('user_agent', '')[:100]
            },
            user_id=str(user_id)
        )
        
        return access_token, refresh_token, {
            'session_id': session_id,
            'expires_at': expires_at.isoformat(),
            'user_id': user_id,
            'username': username
        }
    
    def validate_session(self, token: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Validate session token and return user data"""
        
        try:
            # Decode JWT token
            payload = jwt.decode(
                token, 
                self.jwt_secret_key, 
                algorithms=[self.algorithm],
                audience='cs-gauntlet-client',
                issuer='cs-gauntlet'
            )
            
            user_id = payload.get('user_id')
            session_id = payload.get('session_id')
            
            if not user_id or not session_id:
                return False, None, "Invalid token payload"
            
            # Check session in Redis
            if self.redis_client:
                session_key = f"session:{session_id}"
                session_data_json = self.redis_client.get(session_key)
                
                if not session_data_json:
                    return False, None, "Session not found or expired"
                
                session_data = json.loads(session_data_json)
                
                # Verify session is active
                if not session_data.get('active', False):
                    return False, None, "Session deactivated"
                
                # Verify token hash
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                if session_data.get('access_token_hash') != token_hash:
                    return False, None, "Token mismatch"
                
                # Update last activity
                session_data['last_activity'] = datetime.utcnow().isoformat()
                self.redis_client.setex(
                    session_key,
                    self.session_timeout,
                    json.dumps(session_data)
                )
                
                # Return user data
                user_data = {
                    'user_id': user_id,
                    'username': payload.get('username'),
                    'session_id': session_id,
                    'expires_at': datetime.fromtimestamp(payload.get('exp')),
                    'additional_claims': session_data.get('additional_claims', {})
                }
                
                return True, user_data, None
            
            else:
                # Fallback without Redis
                user_data = {
                    'user_id': user_id,
                    'username': payload.get('username'),
                    'session_id': session_id,
                    'expires_at': datetime.fromtimestamp(payload.get('exp'))
                }
                return True, user_data, None
                
        except jwt.ExpiredSignatureError:
            return False, None, "Token expired"
        except jwt.InvalidTokenError as e:
            return False, None, f"Invalid token: {str(e)}"
        except Exception as e:
            return False, None, f"Session validation error: {str(e)}"
    
    def refresh_session(self, refresh_token: str) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """Refresh an access token using refresh token"""
        
        try:
            # Decode refresh token
            payload = jwt.decode(
                refresh_token,
                self.jwt_secret_key,
                algorithms=[self.algorithm]
            )
            
            if payload.get('type') != 'refresh':
                return False, None, None, "Invalid refresh token type"
            
            user_id = payload.get('user_id')
            session_id = payload.get('session_id')
            
            # Validate session exists
            if self.redis_client:
                session_key = f"session:{session_id}"
                session_data_json = self.redis_client.get(session_key)
                
                if not session_data_json:
                    return False, None, None, "Session not found"
                
                session_data = json.loads(session_data_json)
                
                if not session_data.get('active', False):
                    return False, None, None, "Session deactivated"
                
                # Verify refresh token hash
                refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
                if session_data.get('refresh_token_hash') != refresh_hash:
                    return False, None, None, "Refresh token mismatch"
            
            # Get user data
            user = User.query.get(user_id)
            if not user:
                return False, None, None, "User not found"
            
            # Create new session
            new_access_token, new_refresh_token, session_info = self.create_session(
                user_id=user.id,
                username=user.username,
                additional_claims=session_data.get('additional_claims') if self.redis_client else None
            )
            
            # Invalidate old session
            if self.redis_client:
                self.invalidate_session(session_id)
            
            return True, new_access_token, new_refresh_token, None
            
        except jwt.ExpiredSignatureError:
            return False, None, None, "Refresh token expired"
        except jwt.InvalidTokenError:
            return False, None, None, "Invalid refresh token"
        except Exception as e:
            return False, None, None, f"Refresh error: {str(e)}"
    
    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a specific session"""
        
        try:
            if self.redis_client:
                session_key = f"session:{session_id}"
                session_data_json = self.redis_client.get(session_key)
                
                if session_data_json:
                    session_data = json.loads(session_data_json)
                    user_id = session_data.get('user_id')
                    
                    # Mark session as inactive
                    session_data['active'] = False
                    session_data['invalidated_at'] = datetime.utcnow().isoformat()
                    
                    self.redis_client.setex(
                        session_key,
                        3600,  # Keep for 1 hour for audit
                        json.dumps(session_data)
                    )
                    
                    # Remove from user sessions
                    if user_id:
                        user_sessions_key = f"user_sessions:{user_id}"
                        self.redis_client.srem(user_sessions_key, session_id)
                    
                    return True
            
            return False
            
        except Exception as e:
            current_app.logger.error(f"Session invalidation error: {e}")
            return False
    
    def invalidate_all_user_sessions(self, user_id: int) -> int:
        """Invalidate all sessions for a user"""
        
        try:
            if not self.redis_client:
                return 0
            
            user_sessions_key = f"user_sessions:{user_id}"
            session_ids = self.redis_client.smembers(user_sessions_key)
            
            count = 0
            for session_id in session_ids:
                if self.invalidate_session(session_id.decode()):
                    count += 1
            
            # Clear user sessions set
            self.redis_client.delete(user_sessions_key)
            
            # Log security event
            from .security import SecurityAudit
            SecurityAudit.log_security_event(
                event_type=AuditEventType.LOGOUT,
                severity=AuditSeverity.MEDIUM,
                success=True,
                message="All user sessions invalidated",
                details={'sessions_invalidated': count},
                user_id=str(user_id)
            )
            
            return count
            
        except Exception as e:
            current_app.logger.error(f"Bulk session invalidation error: {e}")
            return 0
    
    def get_user_sessions(self, user_id: int) -> list:
        """Get all active sessions for a user"""
        
        if not self.redis_client:
            return []
        
        try:
            user_sessions_key = f"user_sessions:{user_id}"
            session_ids = self.redis_client.smembers(user_sessions_key)
            
            sessions = []
            for session_id in session_ids:
                session_key = f"session:{session_id.decode()}"
                session_data_json = self.redis_client.get(session_key)
                
                if session_data_json:
                    session_data = json.loads(session_data_json)
                    if session_data.get('active', False):
                        sessions.append({
                            'session_id': session_id.decode(),
                            'created_at': session_data.get('created_at'),
                            'last_activity': session_data.get('last_activity'),
                            'ip_address': session_data.get('ip_address'),
                            'user_agent': session_data.get('user_agent', '')[:50] + '...' if len(session_data.get('user_agent', '')) > 50 else session_data.get('user_agent', '')
                        })
            
            return sessions
            
        except Exception as e:
            current_app.logger.error(f"Get user sessions error: {e}")
            return []
    
    def _generate_session_id(self) -> str:
        """Generate cryptographically secure session ID"""
        return secrets.token_urlsafe(32)
    
    def _cleanup_user_sessions(self, user_id: int):
        """Clean up old sessions if user has too many"""
        
        if not self.redis_client:
            return
        
        try:
            user_sessions_key = f"user_sessions:{user_id}"
            session_ids = list(self.redis_client.smembers(user_sessions_key))
            
            if len(session_ids) <= self.max_sessions_per_user:
                return
            
            # Get session data for all sessions
            sessions_with_data = []
            for session_id in session_ids:
                session_key = f"session:{session_id.decode()}"
                session_data_json = self.redis_client.get(session_key)
                
                if session_data_json:
                    session_data = json.loads(session_data_json)
                    sessions_with_data.append((session_id.decode(), session_data))
            
            # Sort by last activity (oldest first)
            sessions_with_data.sort(key=lambda x: x[1].get('last_activity', ''))
            
            # Remove oldest sessions
            sessions_to_remove = len(sessions_with_data) - self.max_sessions_per_user
            for i in range(sessions_to_remove):
                session_id = sessions_with_data[i][0]
                self.invalidate_session(session_id)
                
        except Exception as e:
            current_app.logger.error(f"Session cleanup error: {e}")

# Decorators for session-based authentication

def require_valid_session(f):
    """Decorator to require valid session for API endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for session token
        token = None
        
        # Check Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Check cookie
        elif 'session_token' in request.cookies:
            token = request.cookies.get('session_token')
        
        if not token:
            return {'error': 'Session token required'}, 401
        
        # Validate session
        session_manager = getattr(g, 'session_manager', None)
        if not session_manager:
            return {'error': 'Session manager not available'}, 500
        
        is_valid, user_data, error = session_manager.validate_session(token)
        
        if not is_valid:
            return {'error': f'Invalid session: {error}'}, 401
        
        # Store user data in request context
        g.current_user_data = user_data
        g.session_token = token
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_fresh_session(max_age_minutes: int = 30):
    """Decorator to require recently authenticated session"""
    def decorator(f):
        @wraps(f)
        @require_valid_session
        def decorated_function(*args, **kwargs):
            user_data = g.get('current_user_data')
            if not user_data:
                return {'error': 'User data not available'}, 500
            
            # Check session age
            expires_at = user_data.get('expires_at')
            if expires_at:
                session_age = (datetime.utcnow() - (expires_at - timedelta(hours=24))).total_seconds() / 60
                if session_age > max_age_minutes:
                    return {'error': 'Session too old, please re-authenticate'}, 401
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

# Session middleware

def init_session_security(app, redis_client=None):
    """Initialize session security for the application"""
    
    # Create session manager
    jwt_secret = app.config.get('JWT_SECRET_KEY') or app.config.get('SECRET_KEY')
    session_manager = SessionManager(redis_client, jwt_secret)
    
    @app.before_request
    def before_request():
        """Set up session manager for each request"""
        g.session_manager = session_manager
        
        # Auto-validate session for authenticated requests
        if current_user.is_authenticated:
            # Update session activity if available
            token = request.cookies.get('session_token') or \
                   (request.headers.get('Authorization', '').replace('Bearer ', '') if 
                    request.headers.get('Authorization', '').startswith('Bearer ') else None)
            
            if token:
                is_valid, user_data, error = session_manager.validate_session(token)
                if is_valid:
                    g.current_session_data = user_data
    
    @app.after_request
    def after_request(response):
        """Clean up session data after request"""
        # Set secure session cookies if needed
        if hasattr(g, 'set_session_cookie'):
            token, max_age = g.set_session_cookie
            response.set_cookie(
                'session_token',
                token,
                max_age=max_age,
                secure=session_manager.secure_cookies,
                httponly=True,
                samesite='Strict'
            )
        
        return response
    
    return session_manager

# Utility functions

def create_session_for_user(user: User, additional_claims: Dict = None) -> Tuple[str, str]:
    """Helper function to create session for a user"""
    session_manager = getattr(g, 'session_manager')
    if not session_manager:
        raise RuntimeError("Session manager not initialized")
    
    access_token, refresh_token, session_info = session_manager.create_session(
        user_id=user.id,
        username=user.username,
        additional_claims=additional_claims
    )
    
    return access_token, refresh_token

def invalidate_current_session():
    """Helper function to invalidate current session"""
    session_manager = getattr(g, 'session_manager')
    current_session = getattr(g, 'current_session_data')
    
    if session_manager and current_session:
        session_id = current_session.get('session_id')
        if session_id:
            return session_manager.invalidate_session(session_id)
    
    return False

def get_current_session_info() -> Optional[Dict]:
    """Get current session information"""
    return getattr(g, 'current_session_data', None)