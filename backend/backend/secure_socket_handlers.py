"""
Secure WebSocket/SocketIO event handlers with comprehensive security
Replaces game_socket_handlers.py with enhanced security features
"""

from flask_socketio import emit, join_room, leave_room, disconnect
from flask_login import current_user
from flask import request, current_app
from datetime import datetime, timedelta
import json
import time
import hashlib
from functools import wraps
from typing import Dict, Set, Optional

from . import socketio, db
from .models import User, GameMode
from .game_manager import game_manager, GameConfig, GameState
from .security import SecurityValidator, SecurityAudit
from .audit_logger import AuditEventType, AuditSeverity
from .rate_limiting import AdvancedRateLimiter

# Security tracking
connected_users: Dict[str, Dict] = {}  # socket_id -> user_info
user_games: Dict[str, str] = {}  # socket_id -> game_id
failed_auth_attempts: Dict[str, list] = {}  # ip -> [timestamps]
suspicious_ips: Set[str] = set()
socket_rate_limiter = None

# Initialize rate limiter for sockets
def init_socket_security(redis_client=None):
    """Initialize socket security components"""
    global socket_rate_limiter
    if redis_client:
        socket_rate_limiter = AdvancedRateLimiter(redis_client)

def socket_auth_required(f):
    """Decorator to require authentication for socket events"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            emit('auth_error', {
                'message': 'Authentication required',
                'event': f.__name__,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Log unauthorized attempt
            SecurityAudit.log_security_event(
                event_type=AuditEventType.ACCESS_DENIED,
                severity=AuditSeverity.MEDIUM,
                success=False,
                message=f"Unauthenticated socket event: {f.__name__}",
                details={'event': f.__name__, 'socket_id': request.sid}
            )
            return
        
        return f(*args, **kwargs)
    return decorated_function

def socket_rate_limit(max_requests: int = 10, window: int = 60):
    """Rate limiting decorator for socket events"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if socket_rate_limiter:
                client_ip = request.remote_addr
                rate_key = f"socket_rate:{client_ip}:{f.__name__}"
                
                if not socket_rate_limiter.is_allowed(rate_key, max_requests, window):
                    emit('rate_limit_error', {
                        'message': f'Rate limit exceeded for {f.__name__}',
                        'retry_after': window
                    })
                    
                    SecurityAudit.log_security_event(
                        event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
                        severity=AuditSeverity.HIGH,
                        success=False,
                        message=f"Socket rate limit exceeded: {f.__name__}",
                        details={'event': f.__name__, 'ip': client_ip}
                    )
                    return
                
                socket_rate_limiter.record_request(rate_key)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_socket_data(schema: Dict):
    """Decorator to validate socket event data"""
    def decorator(f):
        @wraps(f)
        def decorated_function(data=None, *args, **kwargs):
            if data is None:
                data = {}
            
            # Validate data against schema
            for field, rules in schema.items():
                value = data.get(field)
                
                if rules.get('required', False) and not value:
                    emit('validation_error', {
                        'message': f'Field {field} is required',
                        'field': field
                    })
                    return
                
                if value:
                    # Type validation
                    expected_type = rules.get('type')
                    if expected_type == 'string' and not isinstance(value, str):
                        emit('validation_error', {'message': f'{field} must be a string'})
                        return
                    elif expected_type == 'integer' and not isinstance(value, int):
                        emit('validation_error', {'message': f'{field} must be an integer'})
                        return
                    
                    # Length validation
                    max_length = rules.get('max_length')
                    if max_length and isinstance(value, str) and len(value) > max_length:
                        emit('validation_error', {'message': f'{field} exceeds maximum length'})
                        return
                    
                    # Pattern validation
                    pattern = rules.get('pattern')
                    if pattern:
                        is_valid, error_msg = SecurityValidator.validate_input(value, pattern)
                        if not is_valid:
                            emit('validation_error', {'message': error_msg})
                            return
                    
                    # Sanitize strings
                    if isinstance(value, str):
                        data[field] = SecurityValidator.sanitize_text(value, max_length or 1000)
            
            return f(data, *args, **kwargs)
        return decorated_function
    return decorator

def check_suspicious_activity(f):
    """Decorator to monitor for suspicious socket activity"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.remote_addr
        socket_id = request.sid
        
        # Check if IP is flagged as suspicious
        if client_ip in suspicious_ips:
            emit('security_warning', {
                'message': 'Your IP has been flagged for suspicious activity'
            })
            
            SecurityAudit.log_security_event(
                event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                severity=AuditSeverity.HIGH,
                success=False,
                message=f"Suspicious IP attempted socket event: {f.__name__}",
                details={'event': f.__name__, 'ip': client_ip}
            )
            return
        
        return f(*args, **kwargs)
    return decorated_function

@socketio.on('connect')
@socket_rate_limit(max_requests=5, window=60)  # Max 5 connections per minute
def handle_secure_connect(auth=None):
    """Handle secure client connection with authentication"""
    client_id = request.sid
    client_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    # Validate connection
    if not _validate_connection(client_ip, user_agent):
        disconnect()
        return
    
    # Store connection info
    connected_users[client_id] = {
        'socket_id': client_id,
        'ip_address': client_ip,
        'user_agent': user_agent,
        'connected_at': datetime.utcnow().isoformat(),
        'authenticated': current_user.is_authenticated,
        'user_id': current_user.id if current_user.is_authenticated else None,
        'username': current_user.username if current_user.is_authenticated else None,
        'last_activity': datetime.utcnow().isoformat()
    }
    
    # Log connection
    SecurityAudit.log_security_event(
        event_type=AuditEventType.DATA_ACCESS,
        severity=AuditSeverity.LOW,
        success=True,
        message="Socket connection established",
        details={
            'socket_id': client_id,
            'authenticated': current_user.is_authenticated,
            'user_agent': user_agent[:100]  # Truncate long user agents
        },
        user_id=str(current_user.id) if current_user.is_authenticated else None
    )
    
    emit('secure_connected', {
        'status': 'connected',
        'client_id': client_id,
        'authenticated': current_user.is_authenticated,
        'timestamp': datetime.utcnow().isoformat(),
        'security_features': ['rate_limiting', 'input_validation', 'audit_logging']
    })
    
    # Send server stats if authenticated
    if current_user.is_authenticated:
        _send_server_stats()

def _validate_connection(client_ip: str, user_agent: str) -> bool:
    """Validate incoming connection"""
    
    # Check if IP is blocked
    if client_ip in suspicious_ips:
        return False
    
    # Validate user agent
    if not user_agent or len(user_agent) < 10 or len(user_agent) > 1000:
        return False
    
    # Check for bot patterns
    bot_patterns = ['bot', 'crawler', 'spider', 'scraper']
    if any(pattern in user_agent.lower() for pattern in bot_patterns):
        return False
    
    # Check connection rate from IP
    current_time = time.time()
    connections_from_ip = sum(
        1 for conn in connected_users.values() 
        if conn['ip_address'] == client_ip and
        (current_time - datetime.fromisoformat(conn['connected_at']).timestamp()) < 300
    )
    
    if connections_from_ip > 10:  # Max 10 connections per IP in 5 minutes
        suspicious_ips.add(client_ip)
        SecurityAudit.log_security_event(
            event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
            severity=AuditSeverity.HIGH,
            success=False,
            message="Too many connections from single IP",
            details={'ip': client_ip, 'connections': connections_from_ip}
        )
        return False
    
    return True

@socketio.on('disconnect')
def handle_secure_disconnect():
    """Handle secure client disconnection"""
    client_id = request.sid
    
    # Get connection info
    conn_info = connected_users.get(client_id, {})
    
    # Handle game disconnection
    if client_id in user_games:
        game_id = user_games[client_id]
        game = game_manager.get_game(game_id)
        
        if game:
            game.remove_player(client_id)
            
            # Notify other players
            emit('player_disconnected', {
                'player_id': client_id,
                'username': conn_info.get('username'),
                'timestamp': datetime.utcnow().isoformat()
            }, room=f"game_{game_id}")
        
        del user_games[client_id]
    
    # Cancel any pending matchmaking
    if conn_info.get('authenticated') and conn_info.get('user_id'):
        game_manager.cancel_matchmaking(conn_info['user_id'], client_id)
    
    # Log disconnection
    SecurityAudit.log_security_event(
        event_type=AuditEventType.DATA_ACCESS,
        severity=AuditSeverity.LOW,
        success=True,
        message="Socket disconnection",
        details={
            'socket_id': client_id,
            'session_duration': _calculate_session_duration(conn_info),
            'authenticated': conn_info.get('authenticated', False)
        },
        user_id=str(conn_info.get('user_id')) if conn_info.get('user_id') else None
    )
    
    # Clean up
    connected_users.pop(client_id, None)
    
    print(f"Client {client_id} disconnected securely. Total: {len(connected_users)}")

@socketio.on('authenticate')
@socket_rate_limit(max_requests=5, window=300)  # Max 5 auth attempts per 5 minutes
@validate_socket_data({
    'token': {'type': 'string', 'required': True, 'max_length': 500}
})
def handle_socket_authenticate(data):
    """Handle socket-level authentication"""
    token = data.get('token')
    client_id = request.sid
    client_ip = request.remote_addr
    
    # Validate token (implement JWT validation here)
    user_id = _validate_auth_token(token)
    
    if user_id:
        # Update connection info
        if client_id in connected_users:
            connected_users[client_id].update({
                'authenticated': True,
                'user_id': user_id,
                'auth_time': datetime.utcnow().isoformat()
            })
        
        emit('authentication_success', {
            'message': 'Socket authenticated successfully',
            'user_id': user_id
        })
        
        SecurityAudit.log_security_event(
            event_type=AuditEventType.LOGIN_SUCCESS,
            severity=AuditSeverity.LOW,
            success=True,
            message="Socket authentication successful",
            user_id=str(user_id)
        )
    else:
        # Track failed attempts
        if client_ip not in failed_auth_attempts:
            failed_auth_attempts[client_ip] = []
        
        failed_auth_attempts[client_ip].append(time.time())
        
        # Clean old attempts
        cutoff = time.time() - 3600  # 1 hour
        failed_auth_attempts[client_ip] = [
            t for t in failed_auth_attempts[client_ip] if t > cutoff
        ]
        
        # Check for too many failures
        if len(failed_auth_attempts[client_ip]) > 10:
            suspicious_ips.add(client_ip)
        
        emit('authentication_failed', {'message': 'Invalid authentication token'})
        
        SecurityAudit.log_security_event(
            event_type=AuditEventType.LOGIN_FAILED,
            severity=AuditSeverity.MEDIUM,
            success=False,
            message="Socket authentication failed",
            details={'token_length': len(token)}
        )

@socketio.on('find_match')
@socket_auth_required
@socket_rate_limit(max_requests=20, window=60)  # Max 20 match requests per minute
@validate_socket_data({
    'game_mode': {'type': 'string', 'required': True, 'pattern': 'game_mode', 'max_length': 20},
    'language': {'type': 'string', 'required': True, 'pattern': 'language', 'max_length': 20}
})
@check_suspicious_activity
def handle_secure_find_match(data):
    """Handle secure matchmaking request"""
    game_mode = data.get('game_mode', 'casual')
    language = data.get('language', 'python')
    client_id = request.sid
    
    # Update last activity
    _update_user_activity(client_id)
    
    # Additional validation
    if not _validate_user_for_matchmaking(current_user):
        emit('matchmaking_error', {'message': 'User not eligible for matchmaking'})
        return
    
    # Find or create match
    found_match, message, game_id = game_manager.find_or_create_match(
        user_id=current_user.id,
        socket_id=client_id,
        username=current_user.username,
        game_mode=game_mode,
        language=language,
        avatar_url=getattr(current_user, 'avatar_url', None),
        college=getattr(current_user, 'college_name', None)
    )
    
    if found_match and game_id:
        # Match found, join game
        user_games[client_id] = game_id
        join_room(f"game_{game_id}")
        
        game = game_manager.get_game(game_id)
        
        emit('match_found', {
            'game_id': game_id,
            'message': message,
            'game_state': game.get_state(),
            'security_verified': True
        })
        
        # Notify all players in the game
        emit('game_updated', {
            'game_state': game.get_state()
        }, room=f"game_{game_id}")
        
        SecurityAudit.log_security_event(
            event_type=AuditEventType.DATA_ACCESS,
            severity=AuditSeverity.LOW,
            success=True,
            message=f"Match found: {game_mode}",
            details={'game_id': game_id, 'language': language},
            user_id=str(current_user.id)
        )
    else:
        # Added to queue
        emit('matchmaking_status', {
            'status': 'searching',
            'message': message,
            'position_in_queue': len(game_manager.matchmaking_queue.get(game_mode, [])),
            'estimated_wait': _estimate_wait_time(game_mode)
        })

@socketio.on('submit_solution')
@socket_auth_required
@socket_rate_limit(max_requests=15, window=60)  # Max 15 submissions per minute
@validate_socket_data({
    'code': {'type': 'string', 'required': True, 'max_length': 50000},
    'language': {'type': 'string', 'required': True, 'pattern': 'language', 'max_length': 20}
})
@check_suspicious_activity
def handle_secure_submit_solution(data):
    """Handle secure solution submission"""
    client_id = request.sid
    
    if client_id not in user_games:
        emit('submission_error', {'message': 'Not in a game'})
        return
    
    code = data.get('code', '').strip()
    language = data.get('language', 'python')
    
    # Additional security validation for code
    is_safe, violations = _validate_code_security(code, language)
    if not is_safe:
        emit('security_violation', {
            'message': 'Code contains security violations',
            'violations': violations
        })
        
        SecurityAudit.log_security_event(
            event_type=AuditEventType.DANGEROUS_CODE_DETECTED,
            severity=AuditSeverity.HIGH,
            success=False,
            message="Dangerous code submitted",
            details={'violations': violations, 'code_length': len(code)},
            user_id=str(current_user.id)
        )
        return
    
    game_id = user_games[client_id]
    game = game_manager.get_game(game_id)
    
    if not game:
        emit('submission_error', {'message': 'Game not found'})
        return
    
    # Check submission timing (anti-cheating)
    if not _validate_submission_timing(game, current_user.id):
        emit('timing_violation', {'message': 'Submission timing suspicious'})
        
        SecurityAudit.log_security_event(
            event_type=AuditEventType.CHEATING_DETECTED,
            severity=AuditSeverity.HIGH,
            success=False,
            message="Suspicious submission timing",
            details={'game_id': game_id},
            user_id=str(current_user.id)
        )
        return
    
    success, message = game.submit_solution(client_id, code, language)
    
    if success:
        emit('solution_submitted', {
            'message': message,
            'round': game.current_round,
            'timestamp': datetime.utcnow().isoformat(),
            'security_validated': True
        })
        
        # Notify other players (without showing the code)
        emit('player_submitted', {
            'player_id': client_id,
            'username': current_user.username,
            'round': game.current_round,
            'timestamp': datetime.utcnow().isoformat()
        }, room=f"game_{game_id}", include_self=False)
        
        SecurityAudit.log_security_event(
            event_type=AuditEventType.CODE_EXECUTION,
            severity=AuditSeverity.MEDIUM,
            success=True,
            message="Code solution submitted",
            details={
                'game_id': game_id,
                'round': game.current_round,
                'code_length': len(code),
                'language': language
            },
            user_id=str(current_user.id)
        )
        
        # Check if round is complete
        current_round = game.rounds[-1] if game.rounds else None
        if current_round and len(current_round.submissions) >= len(game.players):
            emit('round_complete', {
                'round': game.current_round,
                'game_state': game.get_state()
            }, room=f"game_{game_id}")
    else:
        emit('submission_error', {'message': message})

@socketio.on('send_chat_message')
@socket_auth_required
@socket_rate_limit(max_requests=30, window=60)  # Max 30 messages per minute
@validate_socket_data({
    'message': {'type': 'string', 'required': True, 'max_length': 200}
})
@check_suspicious_activity
def handle_secure_chat_message(data):
    """Handle secure in-game chat messages"""
    client_id = request.sid
    
    if client_id not in user_games:
        emit('chat_error', {'message': 'Not in a game'})
        return
    
    message = data.get('message', '').strip()
    
    # Content filtering
    if not _validate_chat_message(message):
        emit('chat_violation', {'message': 'Message contains inappropriate content'})
        
        SecurityAudit.log_security_event(
            event_type=AuditEventType.SECURITY_VIOLATION,
            severity=AuditSeverity.MEDIUM,
            success=False,
            message="Inappropriate chat message blocked",
            details={'message_length': len(message)},
            user_id=str(current_user.id)
        )
        return
    
    game_id = user_games[client_id]
    
    chat_message = {
        'id': f"msg_{hashlib.sha256(f'{client_id}{time.time()}'.encode()).hexdigest()[:8]}",
        'user_id': current_user.id,
        'username': current_user.username,
        'message': SecurityValidator.sanitize_html(message),
        'timestamp': datetime.utcnow().isoformat(),
        'avatar_url': getattr(current_user, 'avatar_url', None),
        'verified': True
    }
    
    # Broadcast to game room
    emit('chat_message', chat_message, room=f"game_{game_id}")

# Helper functions

def _calculate_session_duration(conn_info: Dict) -> Optional[float]:
    """Calculate session duration in seconds"""
    try:
        connected_at = datetime.fromisoformat(conn_info.get('connected_at', ''))
        return (datetime.utcnow() - connected_at).total_seconds()
    except:
        return None

def _validate_auth_token(token: str) -> Optional[int]:
    """Validate authentication token and return user ID"""
    # Implement JWT token validation here
    # For now, return None (not implemented)
    return None

def _update_user_activity(client_id: str):
    """Update user's last activity timestamp"""
    if client_id in connected_users:
        connected_users[client_id]['last_activity'] = datetime.utcnow().isoformat()

def _validate_user_for_matchmaking(user: User) -> bool:
    """Validate if user is eligible for matchmaking"""
    # Add business logic validation
    # Check for bans, restrictions, etc.
    return True

def _estimate_wait_time(game_mode: str) -> int:
    """Estimate wait time for matchmaking in seconds"""
    queue_length = len(game_manager.matchmaking_queue.get(game_mode, []))
    return min(queue_length * 30, 300)  # Max 5 minutes

def _validate_code_security(code: str, language: str) -> tuple:
    """Validate code for security issues"""
    is_valid, error_or_code = SecurityValidator.validate_code_input(code, language)
    if not is_valid:
        return False, [error_or_code]
    return True, []

def _validate_submission_timing(game, user_id: int) -> bool:
    """Validate submission timing to prevent cheating"""
    if not game.rounds:
        return True
    
    current_round = game.rounds[-1]
    if not current_round.start_time:
        return True
    
    # Check minimum time (prevent instant submissions)
    elapsed = (datetime.utcnow() - current_round.start_time).total_seconds()
    
    if elapsed < 10:  # Minimum 10 seconds to read problem
        return False
    
    return True

def _validate_chat_message(message: str) -> bool:
    """Validate chat message content"""
    # Basic profanity filter
    banned_words = [
        'spam', 'cheat', 'hack', 'exploit', 'bot', 'script',
        # Add more as needed
    ]
    
    message_lower = message.lower()
    for word in banned_words:
        if word in message_lower:
            return False
    
    # Check for suspicious patterns
    if message.count('http://') + message.count('https://') > 0:
        return False  # No URLs in chat
    
    return True

def _send_server_stats():
    """Send server statistics to authenticated users"""
    emit('server_stats', {
        'online_users': len([u for u in connected_users.values() if u.get('authenticated')]),
        'active_games': game_manager.get_active_games_count(),
        'matchmaking_queue': game_manager.get_matchmaking_stats(),
        'timestamp': datetime.utcnow().isoformat(),
        'security_status': 'active'
    })

# Error handlers
@socketio.on_error_default
def default_error_handler(e):
    """Handle socket errors with security logging"""
    client_id = request.sid
    
    SecurityAudit.log_security_event(
        event_type=AuditEventType.SYSTEM_ERROR,
        severity=AuditSeverity.HIGH,
        success=False,
        message=f"Socket error: {str(e)}",
        details={'socket_id': client_id, 'error_type': type(e).__name__}
    )
    
    emit('error', {
        'message': 'An unexpected error occurred',
        'error_id': hashlib.sha256(f"{client_id}{time.time()}".encode()).hexdigest()[:8]
    })

# Cleanup function
def cleanup_socket_connections():
    """Clean up stale socket connections"""
    current_time = datetime.utcnow()
    stale_connections = []
    
    for socket_id, conn_info in connected_users.items():
        try:
            last_activity = datetime.fromisoformat(conn_info.get('last_activity', ''))
            if (current_time - last_activity).total_seconds() > 3600:  # 1 hour
                stale_connections.append(socket_id)
        except:
            stale_connections.append(socket_id)
    
    for socket_id in stale_connections:
        connected_users.pop(socket_id, None)
        user_games.pop(socket_id, None)

# Broadcast security updates
def broadcast_security_alert(alert_type: str, message: str):
    """Broadcast security alerts to all connected users"""
    socketio.emit('security_alert', {
        'type': alert_type,
        'message': message,
        'timestamp': datetime.utcnow().isoformat()
    })