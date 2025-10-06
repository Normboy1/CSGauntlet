"""
Secure Authentication Routes and Middleware
Integrates session security with Flask-Login and existing auth system
"""

from flask import Blueprint, request, jsonify, g, current_app, make_response
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta
import json

from .models import User, db
from .session_security import SessionManager, require_valid_session, create_session_for_user
from .security import SecurityValidator, SecurityAudit
from .audit_logger import AuditEventType, AuditSeverity
from .rate_limiting import AdvancedRateLimiter

secure_auth = Blueprint('secure_auth', __name__, url_prefix='/api/auth')

@secure_auth.route('/login', methods=['POST'])
def secure_login():
    """Secure login endpoint with session management"""
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate input
        username = data.get('username', '').strip()
        password = data.get('password', '')
        remember_me = data.get('remember_me', False)
        
        # Security validation
        if not SecurityValidator.validate_input(username, 'username')[0]:
            return jsonify({'error': 'Invalid username format'}), 400
        
        if not SecurityValidator.validate_input(password, 'password')[0]:
            return jsonify({'error': 'Invalid password format'}), 400
        
        # Rate limiting
        rate_limiter = getattr(g, 'rate_limiter', None)
        if rate_limiter:
            client_ip = request.remote_addr
            rate_key = f"login_attempts:{client_ip}"
            
            if not rate_limiter.is_allowed(rate_key, max_requests=5, window=300):  # 5 attempts per 5 minutes
                SecurityAudit.log_security_event(
                    event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
                    severity=AuditSeverity.HIGH,
                    success=False,
                    message="Login rate limit exceeded",
                    details={'ip': client_ip}
                )
                return jsonify({'error': 'Too many login attempts. Try again later.'}), 429
        
        # Find user
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            # Log failed attempt
            SecurityAudit.log_security_event(
                event_type=AuditEventType.LOGIN_FAILED,
                severity=AuditSeverity.MEDIUM,
                success=False,
                message="Invalid login credentials",
                details={
                    'username': username,
                    'ip': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', '')[:100]
                }
            )
            
            # Record failed attempt for rate limiting
            if rate_limiter:
                rate_limiter.record_request(rate_key)
            
            return jsonify({'error': 'Invalid username or password'}), 401
        
        # Check if user is active
        if hasattr(user, 'is_active') and not user.is_active:
            SecurityAudit.log_security_event(
                event_type=AuditEventType.LOGIN_FAILED,
                severity=AuditSeverity.MEDIUM,
                success=False,
                message="Inactive user login attempt",
                details={'username': username},
                user_id=str(user.id)
            )
            return jsonify({'error': 'Account is deactivated'}), 403
        
        # Login with Flask-Login
        login_user(user, remember=remember_me)
        
        # Create secure session
        session_manager = getattr(g, 'session_manager')
        if session_manager:
            # Additional claims for session
            additional_claims = {
                'login_method': 'password',
                'ip_address': request.remote_addr,
                'user_agent_hash': SecurityValidator.hash_string(
                    request.headers.get('User-Agent', '')
                )[:16],
                'permissions': _get_user_permissions(user)
            }
            
            access_token, refresh_token, session_info = session_manager.create_session(
                user_id=user.id,
                username=user.username,
                additional_claims=additional_claims
            )
            
            # Prepare response
            response_data = {
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'college_name': getattr(user, 'college_name', ''),
                    'avatar_url': getattr(user, 'avatar_url', None)
                },
                'session': {
                    'expires_at': session_info['expires_at'],
                    'session_id': session_info['session_id']
                },
                'tokens': {
                    'access_token': access_token,
                    'refresh_token': refresh_token
                }
            }
            
            # Create response with secure cookies
            response = make_response(jsonify(response_data))
            
            # Set secure session cookies
            cookie_max_age = 86400 * 30 if remember_me else 86400  # 30 days or 1 day
            
            response.set_cookie(
                'session_token',
                access_token,
                max_age=cookie_max_age,
                secure=current_app.config.get('ENV') == 'production',
                httponly=True,
                samesite='Strict'
            )
            
            response.set_cookie(
                'refresh_token',
                refresh_token,
                max_age=86400 * 30,  # 30 days
                secure=current_app.config.get('ENV') == 'production',
                httponly=True,
                samesite='Strict'
            )
            
        else:
            # Fallback without session manager
            response_data = {
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'college_name': getattr(user, 'college_name', ''),
                    'avatar_url': getattr(user, 'avatar_url', None)
                }
            }
            response = make_response(jsonify(response_data))
        
        # Update user last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Log successful login
        SecurityAudit.log_security_event(
            event_type=AuditEventType.LOGIN_SUCCESS,
            severity=AuditSeverity.LOW,
            success=True,
            message="User login successful",
            details={
                'login_method': 'password',
                'ip': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', '')[:100]
            },
            user_id=str(user.id)
        )
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Login error: {e}")
        return jsonify({'error': 'Login failed due to server error'}), 500

@secure_auth.route('/logout', methods=['POST'])
@login_required
def secure_logout():
    """Secure logout endpoint"""
    
    try:
        user_id = current_user.id
        
        # Invalidate current session
        session_manager = getattr(g, 'session_manager')
        if session_manager:
            # Get current session info
            current_session = getattr(g, 'current_session_data')
            if current_session:
                session_id = current_session.get('session_id')
                if session_id:
                    session_manager.invalidate_session(session_id)
        
        # Logout with Flask-Login
        logout_user()
        
        # Log logout
        SecurityAudit.log_security_event(
            event_type=AuditEventType.LOGOUT,
            severity=AuditSeverity.LOW,
            success=True,
            message="User logout",
            user_id=str(user_id)
        )
        
        # Clear session cookies
        response = make_response(jsonify({
            'success': True,
            'message': 'Logout successful'
        }))
        
        response.set_cookie('session_token', '', expires=0)
        response.set_cookie('refresh_token', '', expires=0)
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Logout error: {e}")
        return jsonify({'error': 'Logout failed'}), 500

@secure_auth.route('/logout-all', methods=['POST'])
@login_required
def logout_all_sessions():
    """Logout from all sessions"""
    
    try:
        session_manager = getattr(g, 'session_manager')
        if session_manager:
            count = session_manager.invalidate_all_user_sessions(current_user.id)
            message = f"Logged out from {count} sessions"
        else:
            message = "Current session logged out"
        
        # Logout current session
        logout_user()
        
        # Clear cookies
        response = make_response(jsonify({
            'success': True,
            'message': message
        }))
        
        response.set_cookie('session_token', '', expires=0)
        response.set_cookie('refresh_token', '', expires=0)
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Logout all error: {e}")
        return jsonify({'error': 'Logout failed'}), 500

@secure_auth.route('/refresh', methods=['POST'])
def refresh_token():
    """Refresh access token using refresh token"""
    
    try:
        # Get refresh token
        refresh_token_value = None
        
        # Check request body
        data = request.get_json()
        if data and 'refresh_token' in data:
            refresh_token_value = data['refresh_token']
        
        # Check cookie
        elif 'refresh_token' in request.cookies:
            refresh_token_value = request.cookies.get('refresh_token')
        
        if not refresh_token_value:
            return jsonify({'error': 'Refresh token required'}), 400
        
        # Refresh session
        session_manager = getattr(g, 'session_manager')
        if not session_manager:
            return jsonify({'error': 'Session manager not available'}), 500
        
        success, new_access_token, new_refresh_token, error = session_manager.refresh_session(
            refresh_token_value
        )
        
        if not success:
            SecurityAudit.log_security_event(
                event_type=AuditEventType.TOKEN_REFRESH_FAILED,
                severity=AuditSeverity.MEDIUM,
                success=False,
                message=f"Token refresh failed: {error}",
                details={'ip': request.remote_addr}
            )
            
            # Clear invalid refresh token
            response = make_response(jsonify({'error': f'Token refresh failed: {error}'}), 401)
            response.set_cookie('refresh_token', '', expires=0)
            return response
        
        # Return new tokens
        response_data = {
            'success': True,
            'message': 'Token refreshed successfully',
            'tokens': {
                'access_token': new_access_token,
                'refresh_token': new_refresh_token
            }
        }
        
        response = make_response(jsonify(response_data))
        
        # Update cookies
        response.set_cookie(
            'session_token',
            new_access_token,
            max_age=86400,  # 1 day
            secure=current_app.config.get('ENV') == 'production',
            httponly=True,
            samesite='Strict'
        )
        
        response.set_cookie(
            'refresh_token',
            new_refresh_token,
            max_age=86400 * 30,  # 30 days
            secure=current_app.config.get('ENV') == 'production',
            httponly=True,
            samesite='Strict'
        )
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Token refresh error: {e}")
        return jsonify({'error': 'Token refresh failed'}), 500

@secure_auth.route('/sessions', methods=['GET'])
@require_valid_session
def get_user_sessions():
    """Get all active sessions for current user"""
    
    try:
        user_data = g.current_user_data
        session_manager = getattr(g, 'session_manager')
        
        if not session_manager:
            return jsonify({'error': 'Session manager not available'}), 500
        
        sessions = session_manager.get_user_sessions(user_data['user_id'])
        
        return jsonify({
            'success': True,
            'sessions': sessions,
            'current_session_id': user_data.get('session_id')
        })
        
    except Exception as e:
        current_app.logger.error(f"Get sessions error: {e}")
        return jsonify({'error': 'Failed to get sessions'}), 500

@secure_auth.route('/sessions/<session_id>', methods=['DELETE'])
@require_valid_session
def revoke_session(session_id):
    """Revoke a specific session"""
    
    try:
        user_data = g.current_user_data
        session_manager = getattr(g, 'session_manager')
        
        if not session_manager:
            return jsonify({'error': 'Session manager not available'}), 500
        
        # Don't allow revoking current session
        if session_id == user_data.get('session_id'):
            return jsonify({'error': 'Cannot revoke current session'}), 400
        
        # Verify session belongs to current user
        user_sessions = session_manager.get_user_sessions(user_data['user_id'])
        session_exists = any(s['session_id'] == session_id for s in user_sessions)
        
        if not session_exists:
            return jsonify({'error': 'Session not found'}), 404
        
        # Revoke session
        success = session_manager.invalidate_session(session_id)
        
        if success:
            SecurityAudit.log_security_event(
                event_type=AuditEventType.SESSION_REVOKED,
                severity=AuditSeverity.MEDIUM,
                success=True,
                message="Session revoked by user",
                details={'revoked_session_id': session_id},
                user_id=str(user_data['user_id'])
            )
            
            return jsonify({
                'success': True,
                'message': 'Session revoked successfully'
            })
        else:
            return jsonify({'error': 'Failed to revoke session'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Revoke session error: {e}")
        return jsonify({'error': 'Failed to revoke session'}), 500

@secure_auth.route('/validate', methods=['GET'])
@require_valid_session
def validate_session():
    """Validate current session"""
    
    try:
        user_data = g.current_user_data
        
        return jsonify({
            'success': True,
            'valid': True,
            'user': {
                'id': user_data['user_id'],
                'username': user_data['username'],
                'session_id': user_data['session_id']
            },
            'expires_at': user_data['expires_at'].isoformat() if user_data.get('expires_at') else None
        })
        
    except Exception as e:
        current_app.logger.error(f"Session validation error: {e}")
        return jsonify({'error': 'Session validation failed'}), 500

@secure_auth.route('/change-password', methods=['POST'])
@require_valid_session
def change_password():
    """Change user password with session validation"""
    
    try:
        data = request.get_json()
        user_data = g.current_user_data
        
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        
        # Validate input
        if not SecurityValidator.validate_input(current_password, 'password')[0]:
            return jsonify({'error': 'Invalid current password format'}), 400
        
        if not SecurityValidator.validate_input(new_password, 'password')[0]:
            return jsonify({'error': 'Invalid new password format'}), 400
        
        # Get user
        user = User.query.get(user_data['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Verify current password
        if not user.check_password(current_password):
            SecurityAudit.log_security_event(
                event_type=AuditEventType.PASSWORD_CHANGE_FAILED,
                severity=AuditSeverity.MEDIUM,
                success=False,
                message="Invalid current password for password change",
                user_id=str(user.id)
            )
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Update password
        user.set_password(new_password)
        db.session.commit()
        
        # Invalidate all sessions except current
        session_manager = getattr(g, 'session_manager')
        if session_manager:
            all_sessions = session_manager.get_user_sessions(user.id)
            current_session_id = user_data.get('session_id')
            
            for session in all_sessions:
                if session['session_id'] != current_session_id:
                    session_manager.invalidate_session(session['session_id'])
        
        # Log password change
        SecurityAudit.log_security_event(
            event_type=AuditEventType.PASSWORD_CHANGED,
            severity=AuditSeverity.MEDIUM,
            success=True,
            message="Password changed successfully",
            user_id=str(user.id)
        )
        
        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f"Change password error: {e}")
        return jsonify({'error': 'Password change failed'}), 500

def _get_user_permissions(user: User) -> list:
    """Get user permissions for session claims"""
    permissions = ['user']
    
    # Add admin permissions if applicable
    if hasattr(user, 'is_admin') and user.is_admin:
        permissions.append('admin')
    
    # Add moderator permissions if applicable
    if hasattr(user, 'is_moderator') and user.is_moderator:
        permissions.append('moderator')
    
    return permissions

# Session security middleware initialization
def register_secure_auth(app):
    """Register secure authentication blueprint and middleware"""
    
    app.register_blueprint(secure_auth)
    
    # Initialize session security
    try:
        from . import redis_client
        from .session_security import init_session_security
        
        session_manager = init_session_security(app, redis_client)
        app.logger.info("Secure session management initialized")
        
        return session_manager
        
    except Exception as e:
        app.logger.warning(f"Session security initialization failed: {e}")
        return None