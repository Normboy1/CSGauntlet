import json
import time
import hashlib
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
from flask import request, current_app, g
from functools import wraps
import logging
from logging.handlers import RotatingFileHandler
import os

class AuditEventType(Enum):
    """Types of audit events"""
    
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"
    ACCOUNT_CREATED = "account_created"
    ACCOUNT_DELETED = "account_deleted"
    
    # Authorization events
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    
    # Data access events
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_DELETION = "data_deletion"
    DATA_EXPORT = "data_export"
    
    # Security events
    SECURITY_VIOLATION = "security_violation"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    MALICIOUS_REQUEST = "malicious_request"
    
    # Code execution events
    CODE_EXECUTION = "code_execution"
    CODE_EXECUTION_BLOCKED = "code_execution_blocked"
    DANGEROUS_CODE_DETECTED = "dangerous_code_detected"
    
    # File operations
    FILE_UPLOAD = "file_upload"
    FILE_DOWNLOAD = "file_download"
    FILE_DELETION = "file_deletion"
    
    # System events
    CONFIGURATION_CHANGE = "configuration_change"
    SYSTEM_ERROR = "system_error"
    DATABASE_ERROR = "database_error"
    
    # Game events
    GAME_STARTED = "game_started"
    GAME_COMPLETED = "game_completed"
    SOLUTION_SUBMITTED = "solution_submitted"
    CHEATING_DETECTED = "cheating_detected"

class AuditSeverity(Enum):
    """Severity levels for audit events"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class AuditEvent:
    """Structured audit event"""
    event_type: AuditEventType
    timestamp: datetime
    user_id: Optional[str]
    session_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    endpoint: Optional[str]
    method: Optional[str]
    severity: AuditSeverity
    success: bool
    message: str
    details: Dict[str, Any]
    request_id: Optional[str]
    event_id: str

class AuditLogger:
    """Comprehensive audit logging system"""
    
    def __init__(self, app=None):
        self.app = app
        self._logger = None
        self._event_buffer = []
        self._buffer_lock = threading.Lock()
        self._buffer_size = 1000
        self._flush_interval = 60  # seconds
        self._last_flush = time.time()
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize audit logger with Flask app"""
        self.app = app
        self._setup_logger()
        
        # Register request handlers
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        app.teardown_appcontext(self._teardown_request)
    
    def _setup_logger(self):
        """Setup the audit logger"""
        
        # Create audit logger
        self._logger = logging.getLogger('audit')
        self._logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        for handler in self._logger.handlers[:]:
            self._logger.removeHandler(handler)
        
        # Create audit log directory
        log_dir = self.app.config.get('AUDIT_LOG_DIR', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # Setup rotating file handler
        log_file = os.path.join(log_dir, 'audit.log')
        handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=10
        )
        
        # JSON formatter for structured logging
        formatter = logging.Formatter(
            '%(asctime)s %(levelname)s %(message)s'
        )
        handler.setFormatter(formatter)
        
        self._logger.addHandler(handler)
        
        # Console handler for development
        if self.app.config.get('ENV') == 'development':
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self._logger.addHandler(console_handler)
    
    def _before_request(self):
        """Called before each request"""
        g.audit_start_time = time.time()
        g.audit_request_id = self._generate_request_id()
    
    def _after_request(self, response):
        """Called after each request"""
        
        # Log request completion for sensitive endpoints
        if self._is_sensitive_endpoint(request.endpoint):
            self.log_event(
                event_type=AuditEventType.DATA_ACCESS,
                severity=AuditSeverity.LOW,
                success=200 <= response.status_code < 300,
                message=f"Request to {request.endpoint}",
                details={
                    'status_code': response.status_code,
                    'response_size': len(response.get_data()),
                    'request_time': time.time() - g.get('audit_start_time', time.time())
                }
            )
        
        return response
    
    def _teardown_request(self, exception):
        """Called at the end of each request"""
        if exception:
            self.log_event(
                event_type=AuditEventType.SYSTEM_ERROR,
                severity=AuditSeverity.HIGH,
                success=False,
                message=f"Request exception: {str(exception)}",
                details={'exception_type': type(exception).__name__}
            )
    
    def log_event(self,
                  event_type: AuditEventType,
                  severity: AuditSeverity,
                  success: bool,
                  message: str,
                  details: Optional[Dict[str, Any]] = None,
                  user_id: Optional[str] = None) -> str:
        """Log an audit event"""
        
        # Generate unique event ID
        event_id = self._generate_event_id()
        
        # Get request context information
        if request:
            ip_address = request.remote_addr
            user_agent = request.headers.get('User-Agent', '')
            endpoint = request.endpoint
            method = request.method
            session_id = request.cookies.get('session', '')
            request_id = g.get('audit_request_id')
        else:
            ip_address = None
            user_agent = None
            endpoint = None
            method = None
            session_id = None
            request_id = None
        
        # Create audit event
        event = AuditEvent(
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            user_id=user_id or self._get_current_user_id(),
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            method=method,
            severity=severity,
            success=success,
            message=message,
            details=details or {},
            request_id=request_id,
            event_id=event_id
        )
        
        # Buffer the event
        self._buffer_event(event)
        
        # Immediate logging for critical events
        if severity == AuditSeverity.CRITICAL:
            self._flush_buffer()
        
        return event_id
    
    def _buffer_event(self, event: AuditEvent):
        """Add event to buffer"""
        with self._buffer_lock:
            self._event_buffer.append(event)
            
            # Check if buffer needs flushing
            if (len(self._event_buffer) >= self._buffer_size or
                time.time() - self._last_flush >= self._flush_interval):
                self._flush_buffer()
    
    def _flush_buffer(self):
        """Flush buffered events to log"""
        with self._buffer_lock:
            if not self._event_buffer:
                return
            
            # Write all buffered events
            for event in self._event_buffer:
                log_entry = {
                    'event_id': event.event_id,
                    'event_type': event.event_type.value,
                    'timestamp': event.timestamp.isoformat(),
                    'user_id': event.user_id,
                    'session_id': event.session_id,
                    'ip_address': event.ip_address,
                    'user_agent': event.user_agent,
                    'endpoint': event.endpoint,
                    'method': event.method,
                    'severity': event.severity.value,
                    'success': event.success,
                    'message': event.message,
                    'details': event.details,
                    'request_id': event.request_id
                }
                
                self._logger.info(json.dumps(log_entry))
            
            # Clear buffer
            self._event_buffer.clear()
            self._last_flush = time.time()
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        return hashlib.sha256(
            f"{time.time()}{threading.get_ident()}".encode()
        ).hexdigest()[:16]
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _get_current_user_id(self) -> Optional[str]:
        """Get current user ID from request context"""
        try:
            if hasattr(request, 'current_user') and request.current_user:
                return str(request.current_user.id)
            return None
        except:
            return None
    
    def _is_sensitive_endpoint(self, endpoint: str) -> bool:
        """Check if endpoint is considered sensitive"""
        if not endpoint:
            return False
        
        sensitive_patterns = [
            'auth.',
            'admin.',
            'api.profile',
            'api.upload',
            'submit_code',
            'leaderboard'
        ]
        
        return any(pattern in endpoint for pattern in sensitive_patterns)
    
    def get_events(self, 
                   start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None,
                   event_types: Optional[List[AuditEventType]] = None,
                   user_id: Optional[str] = None,
                   severity: Optional[AuditSeverity] = None,
                   limit: int = 100) -> List[Dict]:
        """Query audit events (for admin interface)"""
        
        # This is a simplified implementation
        # In production, you'd want to use a proper database or search engine
        
        events = []
        
        # Read from log file and parse events
        log_file = os.path.join(
            self.app.config.get('AUDIT_LOG_DIR', 'logs'),
            'audit.log'
        )
        
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            # Parse log line to extract JSON
                            parts = line.strip().split(' ', 3)
                            if len(parts) >= 4:
                                json_part = parts[3]
                                event_data = json.loads(json_part)
                                
                                # Apply filters
                                if self._event_matches_filters(
                                    event_data, start_time, end_time, 
                                    event_types, user_id, severity
                                ):
                                    events.append(event_data)
                                    
                                    if len(events) >= limit:
                                        break
                        except (json.JSONDecodeError, IndexError):
                            continue
            except IOError:
                pass
        
        return list(reversed(events))  # Most recent first
    
    def _event_matches_filters(self,
                             event_data: Dict,
                             start_time: Optional[datetime],
                             end_time: Optional[datetime],
                             event_types: Optional[List[AuditEventType]],
                             user_id: Optional[str],
                             severity: Optional[AuditSeverity]) -> bool:
        """Check if event matches the given filters"""
        
        # Time filter
        if start_time or end_time:
            event_time = datetime.fromisoformat(event_data['timestamp'])
            if start_time and event_time < start_time:
                return False
            if end_time and event_time > end_time:
                return False
        
        # Event type filter
        if event_types:
            event_type_values = [et.value for et in event_types]
            if event_data['event_type'] not in event_type_values:
                return False
        
        # User filter
        if user_id and event_data.get('user_id') != user_id:
            return False
        
        # Severity filter
        if severity and event_data.get('severity') != severity.value:
            return False
        
        return True

# Decorators for automatic audit logging

def audit_login(f):
    """Decorator to audit login attempts"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        audit_logger = current_app.extensions.get('audit_logger')
        
        try:
            result = f(*args, **kwargs)
            
            # Determine if login was successful
            success = False
            user_id = None
            
            if hasattr(result, 'status_code'):
                success = result.status_code == 200
            elif isinstance(result, tuple) and len(result) > 1:
                success = result[1] == 200
            else:
                success = True
            
            # Try to get user ID from request data
            if request.is_json:
                data = request.get_json()
                user_id = data.get('user_id') or data.get('email')
            
            if audit_logger:
                audit_logger.log_event(
                    event_type=AuditEventType.LOGIN_SUCCESS if success else AuditEventType.LOGIN_FAILED,
                    severity=AuditSeverity.MEDIUM if not success else AuditSeverity.LOW,
                    success=success,
                    message=f"Login attempt for user {user_id}",
                    details={'attempted_user': user_id},
                    user_id=user_id if success else None
                )
            
            return result
            
        except Exception as e:
            if audit_logger:
                audit_logger.log_event(
                    event_type=AuditEventType.LOGIN_FAILED,
                    severity=AuditSeverity.HIGH,
                    success=False,
                    message=f"Login exception: {str(e)}",
                    details={'exception': str(e)}
                )
            raise
    
    return decorated_function

def audit_data_access(operation: str = "access"):
    """Decorator to audit data access operations"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            audit_logger = current_app.extensions.get('audit_logger')
            
            try:
                result = f(*args, **kwargs)
                
                success = True
                if hasattr(result, 'status_code'):
                    success = 200 <= result.status_code < 300
                elif isinstance(result, tuple) and len(result) > 1:
                    success = 200 <= result[1] < 300
                
                if audit_logger:
                    event_type_map = {
                        'access': AuditEventType.DATA_ACCESS,
                        'modify': AuditEventType.DATA_MODIFICATION,
                        'delete': AuditEventType.DATA_DELETION,
                        'export': AuditEventType.DATA_EXPORT
                    }
                    
                    audit_logger.log_event(
                        event_type=event_type_map.get(operation, AuditEventType.DATA_ACCESS),
                        severity=AuditSeverity.MEDIUM if operation in ['modify', 'delete'] else AuditSeverity.LOW,
                        success=success,
                        message=f"Data {operation} operation",
                        details={
                            'operation': operation,
                            'function': f.__name__
                        }
                    )
                
                return result
                
            except Exception as e:
                if audit_logger:
                    audit_logger.log_event(
                        event_type=AuditEventType.SYSTEM_ERROR,
                        severity=AuditSeverity.HIGH,
                        success=False,
                        message=f"Data {operation} exception: {str(e)}",
                        details={'exception': str(e), 'function': f.__name__}
                    )
                raise
        
        return decorated_function
    return decorator

def audit_code_execution(f):
    """Decorator to audit code execution"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        audit_logger = current_app.extensions.get('audit_logger')
        
        if audit_logger:
            # Log code execution start
            code_sample = ""
            if request.is_json:
                data = request.get_json()
                code = data.get('code', '')
                code_sample = code[:200] + "..." if len(code) > 200 else code
            
            audit_logger.log_event(
                event_type=AuditEventType.CODE_EXECUTION,
                severity=AuditSeverity.MEDIUM,
                success=True,
                message="Code execution started",
                details={
                    'code_sample': code_sample,
                    'code_length': len(code) if 'code' in locals() else 0
                }
            )
        
        try:
            result = f(*args, **kwargs)
            
            if audit_logger:
                success = True
                if hasattr(result, 'status_code'):
                    success = 200 <= result.status_code < 300
                elif isinstance(result, tuple):
                    success = result[0] if isinstance(result[0], bool) else True
                
                audit_logger.log_event(
                    event_type=AuditEventType.CODE_EXECUTION,
                    severity=AuditSeverity.LOW,
                    success=success,
                    message="Code execution completed",
                    details={'execution_success': success}
                )
            
            return result
            
        except Exception as e:
            if audit_logger:
                audit_logger.log_event(
                    event_type=AuditEventType.CODE_EXECUTION_BLOCKED,
                    severity=AuditSeverity.HIGH,
                    success=False,
                    message=f"Code execution failed: {str(e)}",
                    details={'exception': str(e)}
                )
            raise
    
    return decorated_function

def setup_audit_logging(app):
    """Setup audit logging for the Flask app"""
    
    audit_logger = AuditLogger(app)
    
    # Store in app extensions
    if not hasattr(app, 'extensions'):
        app.extensions = {}
    app.extensions['audit_logger'] = audit_logger
    
    return audit_logger