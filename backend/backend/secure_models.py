"""
Secure Model Mixins and Enhanced Models
Provides security features for SQLAlchemy models including encryption, audit trails, and validation
"""

from datetime import datetime
from typing import Optional, Dict, Any
from flask import current_app, g
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean, event
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
import hashlib
import json

from .database_security import DatabaseSecurity, secure_db_operation, validate_input_fields
from .security import SecurityAudit
from .audit_logger import AuditEventType, AuditSeverity

class SecureModelMixin:
    """Mixin to add security features to SQLAlchemy models"""
    
    @declared_attr
    def created_at(cls):
        return Column(DateTime, default=datetime.utcnow, nullable=False)
    
    @declared_attr
    def updated_at(cls):
        return Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    @declared_attr
    def created_by_ip(cls):
        return Column(String(45))  # IPv6 compatible
    
    @declared_attr
    def last_modified_ip(cls):
        return Column(String(45))
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert model to dictionary with security considerations"""
        
        result = {}
        
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            
            # Skip sensitive fields unless explicitly requested
            if not include_sensitive and self._is_sensitive_field(column.name):
                continue
            
            # Convert datetime to ISO format
            if isinstance(value, datetime):
                value = value.isoformat()
            
            result[column.name] = value
        
        return result
    
    def _is_sensitive_field(self, field_name: str) -> bool:
        """Check if field contains sensitive data"""
        sensitive_patterns = [
            'password', 'secret', 'token', 'key', 'hash',
            'salt', 'ssn', 'credit_card', 'bank_account'
        ]
        
        field_lower = field_name.lower()
        return any(pattern in field_lower for pattern in sensitive_patterns)
    
    @secure_db_operation("model_save")
    def secure_save(self) -> bool:
        """Securely save model with audit logging"""
        
        try:
            from .models import db
            from flask import request
            
            # Set IP address if available
            if request:
                if not self.created_by_ip:
                    self.created_by_ip = request.remote_addr
                self.last_modified_ip = request.remote_addr
            
            db.session.add(self)
            db.session.commit()
            
            # Log model change
            SecurityAudit.log_security_event(
                event_type=AuditEventType.DATA_MODIFICATION,
                severity=AuditSeverity.LOW,
                success=True,
                message=f"Model saved: {self.__class__.__name__}",
                details={
                    'model': self.__class__.__name__,
                    'id': getattr(self, 'id', None)
                }
            )
            
            return True
            
        except Exception as e:
            from .models import db
            db.session.rollback()
            current_app.logger.error(f"Secure save error: {e}")
            return False
    
    @secure_db_operation("model_delete")
    def secure_delete(self) -> bool:
        """Securely delete model with audit logging"""
        
        try:
            from .models import db
            
            model_info = {
                'model': self.__class__.__name__,
                'id': getattr(self, 'id', None)
            }
            
            db.session.delete(self)
            db.session.commit()
            
            # Log deletion
            SecurityAudit.log_security_event(
                event_type=AuditEventType.DATA_DELETION,
                severity=AuditSeverity.MEDIUM,
                success=True,
                message=f"Model deleted: {self.__class__.__name__}",
                details=model_info
            )
            
            return True
            
        except Exception as e:
            from .models import db
            db.session.rollback()
            current_app.logger.error(f"Secure delete error: {e}")
            return False

class EncryptedFieldMixin:
    """Mixin to add encrypted field support to models"""
    
    def _get_db_security(self) -> DatabaseSecurity:
        """Get database security instance"""
        if hasattr(current_app, 'db_security'):
            return current_app.db_security
        else:
            return DatabaseSecurity()
    
    def encrypt_field(self, field_name: str, value: str) -> str:
        """Encrypt a field value for storage"""
        if not value:
            return ""
        
        db_security = self._get_db_security()
        return db_security.encrypt_sensitive_data(value)
    
    def decrypt_field(self, field_name: str, encrypted_value: str) -> str:
        """Decrypt a field value from storage"""
        if not encrypted_value:
            return ""
        
        db_security = self._get_db_security()
        return db_security.decrypt_sensitive_data(encrypted_value)

class AuditTrailMixin:
    """Mixin to add audit trail support to models"""
    
    @declared_attr
    def version(cls):
        return Column(Integer, default=1, nullable=False)
    
    @declared_attr
    def audit_log(cls):
        return Column(Text)  # JSON string of changes
    
    def log_change(self, action: str, changes: Dict[str, Any] = None, user_id: str = None):
        """Log a change to the audit trail"""
        
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'action': action,
            'changes': changes or {},
            'user_id': user_id,
            'ip_address': getattr(g, 'remote_addr', None),
            'version': self.version
        }
        
        # Update audit log
        current_log = json.loads(self.audit_log or '[]')
        current_log.append(audit_entry)
        
        # Keep only last 50 entries
        if len(current_log) > 50:
            current_log = current_log[-50:]
        
        self.audit_log = json.dumps(current_log)
        self.version = (self.version or 0) + 1
    
    def get_audit_history(self) -> list:
        """Get audit history for this model"""
        if not self.audit_log:
            return []
        
        try:
            return json.loads(self.audit_log)
        except:
            return []

class SecureUser(SecureModelMixin, EncryptedFieldMixin, AuditTrailMixin):
    """Enhanced User model with security features"""
    
    __abstract__ = True
    
    # Encrypted fields
    _encrypted_email = Column('email_encrypted', Text)
    _encrypted_phone = Column('phone_encrypted', Text)
    
    # Password security
    password_hash = Column(String(255), nullable=False)
    password_salt = Column(String(64), nullable=False)
    password_changed_at = Column(DateTime, default=datetime.utcnow)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)
    
    # Security tracking
    last_login_ip = Column(String(45))
    last_login_at = Column(DateTime)
    security_questions_hash = Column(Text)
    two_factor_secret = Column(String(32))
    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)
    
    @hybrid_property
    def email(self):
        """Decrypt email for access"""
        if self._encrypted_email:
            return self.decrypt_field('email', self._encrypted_email)
        return None
    
    @email.setter
    def email(self, value):
        """Encrypt email for storage"""
        if value:
            self._encrypted_email = self.encrypt_field('email', value)
        else:
            self._encrypted_email = None
    
    @hybrid_property
    def phone(self):
        """Decrypt phone for access"""
        if self._encrypted_phone:
            return self.decrypt_field('phone', self._encrypted_phone)
        return None
    
    @phone.setter
    def phone(self, value):
        """Encrypt phone for storage"""
        if value:
            self._encrypted_phone = self.encrypt_field('phone', value)
        else:
            self._encrypted_phone = None
    
    @validate_input_fields(password='password')
    def set_password(self, password: str):
        """Set password with secure hashing"""
        db_security = self._get_db_security()
        self.password_hash, self.password_salt = db_security.hash_password(password)
        self.password_changed_at = datetime.utcnow()
        self.failed_login_attempts = 0
        
        # Log password change
        self.log_change('password_changed', user_id=str(getattr(self, 'id', 'unknown')))
    
    def check_password(self, password: str) -> bool:
        """Check password against hash"""
        if not self.password_hash or not self.password_salt:
            return False
        
        db_security = self._get_db_security()
        return db_security.verify_password(password, self.password_hash, self.password_salt)
    
    def is_account_locked(self) -> bool:
        """Check if account is locked due to failed attempts"""
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False
    
    def increment_failed_login(self):
        """Increment failed login attempts and lock if necessary"""
        self.failed_login_attempts = (self.failed_login_attempts or 0) + 1
        
        # Lock account after 5 failed attempts for 30 minutes
        if self.failed_login_attempts >= 5:
            from datetime import timedelta
            self.locked_until = datetime.utcnow() + timedelta(minutes=30)
        
        self.log_change('failed_login_attempt')
    
    def reset_failed_login(self):
        """Reset failed login attempts after successful login"""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login_at = datetime.utcnow()
        self.last_login_ip = getattr(g, 'remote_addr', None)
        
        self.log_change('successful_login')
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert to dict with proper email/phone handling"""
        result = super().to_dict(include_sensitive)
        
        # Include decrypted email/phone if not sensitive
        if not include_sensitive:
            result['email'] = self.email
            result['phone'] = self.phone
            
            # Remove encrypted fields from output
            result.pop('_encrypted_email', None)
            result.pop('_encrypted_phone', None)
            result.pop('password_hash', None)
            result.pop('password_salt', None)
        
        return result

class SecureSubmission(SecureModelMixin, AuditTrailMixin):
    """Enhanced Submission model with security features"""
    
    __abstract__ = True
    
    # Code security
    code_hash = Column(String(64))  # SHA-256 hash of code
    code_length = Column(Integer)
    security_flags = Column(Text)  # JSON of security issues found
    
    # Plagiarism detection
    similarity_hash = Column(String(64))
    similarity_score = Column(Integer, default=0)
    
    def set_code(self, code: str, language: str):
        """Set code with security validation"""
        from .security import SecurityValidator
        
        # Validate code
        is_valid, error_or_code = SecurityValidator.validate_code_input(code, language)
        if not is_valid:
            raise ValueError(f"Code validation failed: {error_or_code}")
        
        # Store metadata
        self.code_hash = hashlib.sha256(code.encode()).hexdigest()
        self.code_length = len(code)
        
        # Generate similarity hash for plagiarism detection
        self.similarity_hash = self._generate_similarity_hash(code)
        
        # Log code submission
        self.log_change('code_submitted', {
            'language': language,
            'code_length': len(code),
            'code_hash': self.code_hash[:8]  # Truncated for logging
        })
    
    def _generate_similarity_hash(self, code: str) -> str:
        """Generate hash for similarity detection"""
        # Normalize code (remove whitespace, comments, etc.)
        import re
        
        # Remove comments and normalize whitespace
        normalized = re.sub(r'#.*?$', '', code, flags=re.MULTILINE)
        normalized = re.sub(r'//.*?$', '', normalized, flags=re.MULTILINE) 
        normalized = re.sub(r'/\*.*?\*/', '', normalized, flags=re.DOTALL)
        normalized = re.sub(r'\s+', ' ', normalized).strip().lower()
        
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    def check_similarity(self, other_code: str) -> int:
        """Check similarity with another code submission"""
        other_hash = self._generate_similarity_hash(other_code)
        
        # Simple similarity check based on hash
        if self.similarity_hash == other_hash:
            return 100  # Identical
        
        # More sophisticated similarity checking could be implemented here
        return 0

# Model event listeners for security

@event.listens_for(SecureUser, 'before_insert')
def before_user_insert(mapper, connection, target):
    """Security checks before user creation"""
    from flask import request
    
    if request:
        target.created_by_ip = request.remote_addr

@event.listens_for(SecureUser, 'before_update')
def before_user_update(mapper, connection, target):
    """Security checks before user update"""
    from flask import request
    
    if request:
        target.last_modified_ip = request.remote_addr

@event.listens_for(SecureSubmission, 'before_insert')
def before_submission_insert(mapper, connection, target):
    """Security checks before submission creation"""
    # Additional security validation could be added here
    pass

# Secure query functions

def secure_get_user_by_username(username: str) -> Optional['User']:
    """Securely get user by username with input validation"""
    from .security import SecurityValidator
    from .models import User
    
    # Validate username
    is_valid, error = SecurityValidator.validate_input(username, 'username')
    if not is_valid:
        current_app.logger.warning(f"Invalid username in query: {error}")
        return None
    
    try:
        return User.query.filter_by(username=username).first()
    except Exception as e:
        current_app.logger.error(f"Secure user query error: {e}")
        return None

def secure_get_user_by_email(email: str) -> Optional['User']:
    """Securely get user by email with input validation"""
    from .security import SecurityValidator
    from .models import User
    
    # Validate email
    is_valid, error = SecurityValidator.validate_input(email, 'email')
    if not is_valid:
        current_app.logger.warning(f"Invalid email in query: {error}")
        return None
    
    try:
        # Note: This is a simplified example. In a real implementation with encrypted emails,
        # you would need to either:
        # 1. Store a hash of the email for querying
        # 2. Use a different approach for email lookups
        return User.query.filter_by(email=email).first()
    except Exception as e:
        current_app.logger.error(f"Secure email query error: {e}")
        return None

@secure_db_operation("get_user_submissions")
def secure_get_user_submissions(user_id: int, limit: int = 50) -> list:
    """Securely get user submissions with input validation"""
    from .models import Submission
    
    try:
        # Validate user_id
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("Invalid user ID")
        
        # Validate limit
        if not isinstance(limit, int) or limit <= 0 or limit > 1000:
            limit = 50
        
        return Submission.query.filter_by(user_id=user_id).limit(limit).all()
        
    except Exception as e:
        current_app.logger.error(f"Secure submissions query error: {e}")
        return []

# Security utilities for models

def check_model_permissions(model_instance, user_id: int, action: str) -> bool:
    """Check if user has permission to perform action on model"""
    
    # Basic ownership check
    if hasattr(model_instance, 'user_id'):
        if model_instance.user_id == user_id:
            return True
    
    # Check admin permissions
    from flask_login import current_user
    if current_user.is_authenticated and hasattr(current_user, 'is_admin'):
        if current_user.is_admin:
            return True
    
    # Model-specific permission logic could be added here
    
    return False

def sanitize_model_output(model_dict: Dict[str, Any], user_role: str = 'user') -> Dict[str, Any]:
    """Sanitize model output based on user role"""
    
    if user_role == 'admin':
        return model_dict
    
    # Remove sensitive fields for regular users
    sensitive_fields = [
        'password_hash', 'password_salt', 'security_questions_hash',
        'two_factor_secret', 'created_by_ip', 'last_modified_ip',
        'failed_login_attempts', 'locked_until'
    ]
    
    for field in sensitive_fields:
        model_dict.pop(field, None)
    
    return model_dict