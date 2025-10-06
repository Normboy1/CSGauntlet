"""
Secure OAuth and GitHub Integration for CS Gauntlet
Provides secure OAuth flows with proper validation, state management, and security monitoring
"""

import secrets
import hashlib
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any
from urllib.parse import urlencode, parse_qs, urlparse
import requests

from flask import Blueprint, request, redirect, url_for, session, jsonify, current_app, g
from flask_login import login_user, current_user

from .models import User, OAuth, db
from .security import SecurityValidator, SecurityAudit
from .audit_logger import AuditEventType, AuditSeverity
from .session_security import create_session_for_user
from .rate_limiting import AdvancedRateLimiter

secure_oauth = Blueprint('secure_oauth', __name__, url_prefix='/auth/oauth')

class OAuthSecurityManager:
    """Manages OAuth security including state validation, token security, and rate limiting"""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.state_timeout = 600  # 10 minutes
        self.nonce_timeout = 600  # 10 minutes
        
        # OAuth provider configurations
        self.providers = {
            'github': {
                'authorize_url': 'https://github.com/login/oauth/authorize',
                'token_url': 'https://github.com/login/oauth/access_token',
                'user_url': 'https://api.github.com/user',
                'emails_url': 'https://api.github.com/user/emails',
                'scope': 'user:email',
                'required_fields': ['id', 'login', 'email']
            }
        }
    
    def generate_state_token(self, provider: str, user_ip: str) -> str:
        """Generate secure OAuth state token"""
        
        # Create state payload
        timestamp = int(time.time())
        random_bytes = secrets.token_bytes(16)
        
        state_data = {
            'provider': provider,
            'timestamp': timestamp,
            'ip': user_ip,
            'nonce': secrets.token_urlsafe(16)
        }
        
        # Create state token
        state_string = json.dumps(state_data, sort_keys=True)
        state_hash = hashlib.sha256(state_string.encode()).hexdigest()
        
        # Store in Redis for validation
        if self.redis_client:
            state_key = f"oauth_state:{state_hash}"
            self.redis_client.setex(state_key, self.state_timeout, state_string)
        
        # Log state generation
        SecurityAudit.log_security_event(
            event_type=AuditEventType.OAUTH_STATE_GENERATED,
            severity=AuditSeverity.LOW,
            success=True,
            message=f"OAuth state generated for {provider}",
            details={'provider': provider, 'state_hash': state_hash[:8]}
        )
        
        return state_hash
    
    def validate_state_token(self, state_token: str, provider: str, user_ip: str) -> Tuple[bool, Optional[str]]:
        """Validate OAuth state token"""
        
        try:
            if not state_token:
                return False, "Missing state token"
            
            # Get stored state
            if self.redis_client:
                state_key = f"oauth_state:{state_token}"
                stored_state = self.redis_client.get(state_key)
                
                if not stored_state:
                    SecurityAudit.log_security_event(
                        event_type=AuditEventType.OAUTH_STATE_INVALID,
                        severity=AuditSeverity.HIGH,
                        success=False,
                        message="OAuth state token not found or expired",
                        details={'provider': provider, 'state_hash': state_token[:8]}
                    )
                    return False, "Invalid or expired state token"
                
                # Parse stored state
                state_data = json.loads(stored_state.decode())
                
                # Validate provider
                if state_data.get('provider') != provider:
                    return False, "Provider mismatch"
                
                # Validate IP (optional, can be disabled in development)
                if current_app.config.get('OAUTH_VALIDATE_IP', True):
                    if state_data.get('ip') != user_ip:
                        SecurityAudit.log_security_event(
                            event_type=AuditEventType.OAUTH_IP_MISMATCH,
                            severity=AuditSeverity.HIGH,
                            success=False,
                            message="OAuth state IP mismatch",
                            details={
                                'provider': provider,
                                'expected_ip': state_data.get('ip'),
                                'actual_ip': user_ip
                            }
                        )
                        return False, "IP address mismatch"
                
                # Validate timestamp
                timestamp = state_data.get('timestamp', 0)
                if time.time() - timestamp > self.state_timeout:
                    return False, "State token expired"
                
                # Delete used state token
                self.redis_client.delete(state_key)
                
                return True, None
            
            else:
                # Fallback validation without Redis
                current_app.logger.warning("OAuth state validation without Redis - security reduced")
                return True, None
                
        except Exception as e:
            current_app.logger.error(f"OAuth state validation error: {e}")
            return False, "State validation failed"
    
    def secure_token_exchange(self, provider: str, code: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Securely exchange authorization code for access token"""
        
        try:
            provider_config = self.providers.get(provider)
            if not provider_config:
                return False, None, "Unsupported provider"
            
            # Prepare token request
            token_data = {
                'client_id': current_app.config.get(f'{provider.upper()}_CLIENT_ID'),
                'client_secret': current_app.config.get(f'{provider.upper()}_CLIENT_SECRET'),
                'code': code,
                'grant_type': 'authorization_code'
            }
            
            if provider == 'github':
                token_data['redirect_uri'] = url_for('secure_oauth.oauth_callback', provider=provider, _external=True)
            
            # Make secure request
            headers = {
                'Accept': 'application/json',
                'User-Agent': 'CS-Gauntlet-OAuth/1.0'
            }
            
            response = requests.post(
                provider_config['token_url'],
                data=token_data,
                headers=headers,
                timeout=30,
                verify=True  # Ensure SSL verification
            )
            
            if response.status_code != 200:
                SecurityAudit.log_security_event(
                    event_type=AuditEventType.OAUTH_TOKEN_FAILED,
                    severity=AuditSeverity.MEDIUM,
                    success=False,
                    message=f"OAuth token exchange failed for {provider}",
                    details={'status_code': response.status_code, 'provider': provider}
                )
                return False, None, f"Token exchange failed: {response.status_code}"
            
            token_response = response.json()
            
            # Validate token response
            if 'access_token' not in token_response:
                return False, None, "No access token in response"
            
            # Log successful token exchange
            SecurityAudit.log_security_event(
                event_type=AuditEventType.OAUTH_TOKEN_SUCCESS,
                severity=AuditSeverity.LOW,
                success=True,
                message=f"OAuth token exchange successful for {provider}",
                details={'provider': provider}
            )
            
            return True, token_response, None
            
        except requests.RequestException as e:
            current_app.logger.error(f"OAuth token request error: {e}")
            return False, None, "Network error during token exchange"
        except Exception as e:
            current_app.logger.error(f"OAuth token exchange error: {e}")
            return False, None, "Token exchange failed"
    
    def fetch_user_data(self, provider: str, access_token: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Securely fetch user data from OAuth provider"""
        
        try:
            provider_config = self.providers.get(provider)
            if not provider_config:
                return False, None, "Unsupported provider"
            
            # Prepare headers
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json',
                'User-Agent': 'CS-Gauntlet-OAuth/1.0'
            }
            
            # Fetch user data
            user_response = requests.get(
                provider_config['user_url'],
                headers=headers,
                timeout=30,
                verify=True
            )
            
            if user_response.status_code != 200:
                return False, None, f"Failed to fetch user data: {user_response.status_code}"
            
            user_data = user_response.json()
            
            # Fetch emails for GitHub
            if provider == 'github':
                emails_response = requests.get(
                    provider_config['emails_url'],
                    headers=headers,
                    timeout=30,
                    verify=True
                )
                
                if emails_response.status_code == 200:
                    emails_data = emails_response.json()
                    # Find primary verified email
                    primary_email = None
                    for email_info in emails_data:
                        if email_info.get('primary') and email_info.get('verified'):
                            primary_email = email_info.get('email')
                            break
                    
                    if primary_email:
                        user_data['email'] = primary_email
            
            # Validate required fields
            for field in provider_config['required_fields']:
                if field not in user_data or not user_data[field]:
                    return False, None, f"Missing required field: {field}"
            
            # Sanitize user data
            sanitized_data = self._sanitize_user_data(user_data, provider)
            
            return True, sanitized_data, None
            
        except requests.RequestException as e:
            current_app.logger.error(f"OAuth user data request error: {e}")
            return False, None, "Network error fetching user data"
        except Exception as e:
            current_app.logger.error(f"OAuth user data fetch error: {e}")
            return False, None, "Failed to fetch user data"
    
    def _sanitize_user_data(self, user_data: Dict, provider: str) -> Dict:
        """Sanitize user data from OAuth provider"""
        
        sanitized = {}
        
        if provider == 'github':
            sanitized = {
                'provider_id': str(user_data.get('id')),
                'username': SecurityValidator.sanitize_text(user_data.get('login', ''), 50),
                'email': SecurityValidator.sanitize_text(user_data.get('email', ''), 255),
                'name': SecurityValidator.sanitize_text(user_data.get('name', ''), 100),
                'avatar_url': user_data.get('avatar_url', ''),
                'profile_url': user_data.get('html_url', ''),
                'bio': SecurityValidator.sanitize_text(user_data.get('bio', ''), 500),
                'location': SecurityValidator.sanitize_text(user_data.get('location', ''), 100),
                'company': SecurityValidator.sanitize_text(user_data.get('company', ''), 100),
                'public_repos': user_data.get('public_repos', 0),
                'followers': user_data.get('followers', 0),
                'following': user_data.get('following', 0)
            }
        
        return sanitized

# Initialize OAuth security manager
oauth_security_manager = None

def init_oauth_security(redis_client=None):
    """Initialize OAuth security manager"""
    global oauth_security_manager
    oauth_security_manager = OAuthSecurityManager(redis_client)
    return oauth_security_manager

@secure_oauth.route('/login/<provider>')
def oauth_login(provider):
    """Initiate OAuth login flow"""
    
    try:
        # Validate provider
        if provider not in oauth_security_manager.providers:
            return jsonify({'error': 'Unsupported OAuth provider'}), 400
        
        # Rate limiting
        rate_limiter = getattr(g, 'rate_limiter', None)
        if rate_limiter:
            client_ip = request.remote_addr
            rate_key = f"oauth_login:{client_ip}:{provider}"
            
            if not rate_limiter.is_allowed(rate_key, max_requests=10, window=300):  # 10 attempts per 5 minutes
                SecurityAudit.log_security_event(
                    event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
                    severity=AuditSeverity.HIGH,
                    success=False,
                    message=f"OAuth login rate limit exceeded for {provider}",
                    details={'provider': provider, 'ip': client_ip}
                )
                return jsonify({'error': 'Rate limit exceeded'}), 429
            
            rate_limiter.record_request(rate_key)
        
        # Generate state token
        state_token = oauth_security_manager.generate_state_token(provider, request.remote_addr)
        
        # Build authorization URL
        provider_config = oauth_security_manager.providers[provider]
        
        auth_params = {
            'client_id': current_app.config.get(f'{provider.upper()}_CLIENT_ID'),
            'redirect_uri': url_for('secure_oauth.oauth_callback', provider=provider, _external=True),
            'scope': provider_config['scope'],
            'state': state_token,
            'response_type': 'code'
        }
        
        # Add provider-specific parameters
        if provider == 'github':
            auth_params['allow_signup'] = 'false'  # Only allow existing GitHub accounts
        
        auth_url = f"{provider_config['authorize_url']}?{urlencode(auth_params)}"
        
        # Log OAuth initiation
        SecurityAudit.log_security_event(
            event_type=AuditEventType.OAUTH_INITIATED,
            severity=AuditSeverity.LOW,
            success=True,
            message=f"OAuth login initiated for {provider}",
            details={'provider': provider, 'state_hash': state_token[:8]}
        )
        
        return redirect(auth_url)
        
    except Exception as e:
        current_app.logger.error(f"OAuth login error: {e}")
        return jsonify({'error': 'OAuth login failed'}), 500

@secure_oauth.route('/callback/<provider>')
def oauth_callback(provider):
    """Handle OAuth callback"""
    
    try:
        # Validate provider
        if provider not in oauth_security_manager.providers:
            return jsonify({'error': 'Unsupported OAuth provider'}), 400
        
        # Get authorization code and state
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        # Check for OAuth errors
        if error:
            SecurityAudit.log_security_event(
                event_type=AuditEventType.OAUTH_FAILED,
                severity=AuditSeverity.MEDIUM,
                success=False,
                message=f"OAuth callback error: {error}",
                details={'provider': provider, 'error': error}
            )
            return redirect(url_for('auth.login', error=f'OAuth error: {error}'))
        
        # Validate required parameters
        if not code or not state:
            SecurityAudit.log_security_event(
                event_type=AuditEventType.OAUTH_INVALID_CALLBACK,
                severity=AuditSeverity.HIGH,
                success=False,
                message="OAuth callback missing required parameters",
                details={'provider': provider, 'has_code': bool(code), 'has_state': bool(state)}
            )
            return redirect(url_for('auth.login', error='Invalid OAuth callback'))
        
        # Validate state token
        is_valid_state, state_error = oauth_security_manager.validate_state_token(
            state, provider, request.remote_addr
        )
        
        if not is_valid_state:
            SecurityAudit.log_security_event(
                event_type=AuditEventType.OAUTH_STATE_INVALID,
                severity=AuditSeverity.HIGH,
                success=False,
                message=f"OAuth state validation failed: {state_error}",
                details={'provider': provider, 'state_hash': state[:8]}
            )
            return redirect(url_for('auth.login', error='Invalid OAuth state'))
        
        # Exchange code for token
        token_success, token_data, token_error = oauth_security_manager.secure_token_exchange(
            provider, code
        )
        
        if not token_success:
            SecurityAudit.log_security_event(
                event_type=AuditEventType.OAUTH_TOKEN_FAILED,
                severity=AuditSeverity.MEDIUM,
                success=False,
                message=f"OAuth token exchange failed: {token_error}",
                details={'provider': provider}
            )
            return redirect(url_for('auth.login', error='OAuth authentication failed'))
        
        # Fetch user data
        user_success, user_data, user_error = oauth_security_manager.fetch_user_data(
            provider, token_data['access_token']
        )
        
        if not user_success:
            SecurityAudit.log_security_event(
                event_type=AuditEventType.OAUTH_USER_FETCH_FAILED,
                severity=AuditSeverity.MEDIUM,
                success=False,
                message=f"OAuth user data fetch failed: {user_error}",
                details={'provider': provider}
            )
            return redirect(url_for('auth.login', error='Failed to fetch user data'))
        
        # Find or create user
        user = _handle_oauth_user(provider, user_data, token_data)
        
        if not user:
            return redirect(url_for('auth.login', error='Failed to process OAuth user'))
        
        # Log in user
        login_user(user, remember=True)
        
        # Create secure session
        session_manager = getattr(g, 'session_manager')
        if session_manager:
            access_token, refresh_token = create_session_for_user(
                user,
                additional_claims={
                    'login_method': f'oauth_{provider}',
                    'oauth_provider': provider,
                    'ip_address': request.remote_addr
                }
            )
        
        # Log successful OAuth login
        SecurityAudit.log_security_event(
            event_type=AuditEventType.OAUTH_LOGIN_SUCCESS,
            severity=AuditSeverity.LOW,
            success=True,
            message=f"OAuth login successful for {provider}",
            details={'provider': provider, 'user_id': user.id},
            user_id=str(user.id)
        )
        
        return redirect(url_for('main.dashboard'))
        
    except Exception as e:
        current_app.logger.error(f"OAuth callback error: {e}")
        SecurityAudit.log_security_event(
            event_type=AuditEventType.OAUTH_FAILED,
            severity=AuditSeverity.HIGH,
            success=False,
            message=f"OAuth callback exception: {str(e)}",
            details={'provider': provider}
        )
        return redirect(url_for('auth.login', error='OAuth authentication failed'))

def _handle_oauth_user(provider: str, user_data: Dict, token_data: Dict) -> Optional[User]:
    """Handle OAuth user creation or update"""
    
    try:
        provider_id = user_data['provider_id']
        email = user_data.get('email')
        
        # Check for existing OAuth connection
        oauth_record = OAuth.query.filter_by(
            provider=provider,
            provider_user_id=provider_id
        ).first()
        
        if oauth_record:
            # Update existing OAuth record
            user = oauth_record.user
            
            # Update OAuth token data
            oauth_record.access_token = token_data.get('access_token')
            oauth_record.refresh_token = token_data.get('refresh_token')
            oauth_record.token_expires_at = _calculate_token_expiry(token_data)
            oauth_record.updated_at = datetime.utcnow()
            
            # Update user profile data
            _update_user_from_oauth(user, user_data, provider)
            
        else:
            # Check for existing user by email
            user = None
            if email:
                user = User.query.filter_by(email=email).first()
            
            if user:
                # Link existing user to OAuth provider
                oauth_record = OAuth(
                    user=user,
                    provider=provider,
                    provider_user_id=provider_id,
                    access_token=token_data.get('access_token'),
                    refresh_token=token_data.get('refresh_token'),
                    token_expires_at=_calculate_token_expiry(token_data),
                    created_at=datetime.utcnow()
                )
                
                db.session.add(oauth_record)
                
                # Update user profile
                _update_user_from_oauth(user, user_data, provider)
                
            else:
                # Create new user
                user = User(
                    username=_generate_unique_username(user_data.get('username', '')),
                    email=email,
                    email_verified=True,  # Email verified by OAuth provider
                    profile_complete=False,
                    created_at=datetime.utcnow()
                )
                
                # Set a random password (user will login via OAuth)
                user.set_password(secrets.token_urlsafe(32))
                
                # Update user profile from OAuth
                _update_user_from_oauth(user, user_data, provider)
                
                db.session.add(user)
                db.session.flush()  # Get user ID
                
                # Create OAuth record
                oauth_record = OAuth(
                    user=user,
                    provider=provider,
                    provider_user_id=provider_id,
                    access_token=token_data.get('access_token'),
                    refresh_token=token_data.get('refresh_token'),
                    token_expires_at=_calculate_token_expiry(token_data),
                    created_at=datetime.utcnow()
                )
                
                db.session.add(oauth_record)
        
        db.session.commit()
        return user
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"OAuth user handling error: {e}")
        return None

def _update_user_from_oauth(user: User, oauth_data: Dict, provider: str):
    """Update user profile from OAuth data"""
    
    if provider == 'github':
        # Update GitHub-specific data
        if oauth_data.get('name') and not user.display_name:
            user.display_name = oauth_data['name']
        
        if oauth_data.get('bio') and not user.bio:
            user.bio = oauth_data['bio']
        
        if oauth_data.get('location') and not user.location:
            user.location = oauth_data['location']
        
        if oauth_data.get('avatar_url'):
            user.avatar_url = oauth_data['avatar_url']
        
        # Store additional GitHub data
        user.github_username = oauth_data.get('username')
        user.github_profile_url = oauth_data.get('profile_url')

def _generate_unique_username(base_username: str) -> str:
    """Generate unique username from OAuth data"""
    
    if not base_username:
        base_username = f"user_{secrets.token_hex(4)}"
    
    # Sanitize username
    base_username = SecurityValidator.sanitize_text(base_username, 30)
    base_username = ''.join(c for c in base_username if c.isalnum() or c in ['_', '-'])
    
    if len(base_username) < 3:
        base_username = f"user_{secrets.token_hex(4)}"
    
    # Check for uniqueness
    username = base_username
    counter = 1
    
    while User.query.filter_by(username=username).first():
        username = f"{base_username}_{counter}"
        counter += 1
        if counter > 1000:  # Prevent infinite loop
            username = f"user_{secrets.token_hex(8)}"
            break
    
    return username

def _calculate_token_expiry(token_data: Dict) -> Optional[datetime]:
    """Calculate token expiry time"""
    
    expires_in = token_data.get('expires_in')
    if expires_in:
        try:
            return datetime.utcnow() + timedelta(seconds=int(expires_in))
        except (ValueError, TypeError):
            pass
    
    # Default to 1 hour if no expiry specified
    return datetime.utcnow() + timedelta(hours=1)

# Register OAuth blueprint
def register_secure_oauth(app):
    """Register secure OAuth blueprint"""
    
    app.register_blueprint(secure_oauth)
    
    # Initialize OAuth security
    try:
        from . import redis_client
        oauth_manager = init_oauth_security(redis_client)
        app.logger.info("Secure OAuth integration initialized")
        return oauth_manager
        
    except Exception as e:
        app.logger.warning(f"OAuth security initialization failed: {e}")
        return None