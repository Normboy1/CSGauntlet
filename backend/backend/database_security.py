"""
Database Security and Query Protection for CS Gauntlet
Provides SQL injection protection, data encryption, and secure query patterns
"""

import re
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from flask import current_app, g
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, event
from sqlalchemy.pool import Pool
from sqlalchemy.engine import Engine
from cryptography.fernet import Fernet
from functools import wraps
import logging

from .security import SecurityValidator, SecurityAudit
from .audit_logger import AuditEventType, AuditSeverity

class DatabaseSecurity:
    """Core database security functions"""
    
    def __init__(self, encryption_key: str = None):
        """Initialize database security"""
        
        # Initialize encryption
        if encryption_key:
            self.encryption_key = encryption_key.encode()
        else:
            self.encryption_key = Fernet.generate_key()
        
        self.cipher = Fernet(self.encryption_key)
        
        # SQL injection patterns to detect
        self.sql_injection_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|SCRIPT)\b)",
            r"(--|\*\/|\*\*|@@|char|nchar|varchar|nvarchar|alter|begin|cast|create|cursor|declare|delete|drop|end|exec|execute|fetch|insert|select|sys|sysobjects|syscolumns|table|update)",
            r"(\b(AND|OR)\s+\d+\s*=\s*\d+)",
            r"([\'\"][;]*(\s)*(union|select|insert|update|delete|drop|create|alter))",
            r"([\'\"][\s]*[\+])",
            r"(union[\s\w]*select)",
            r"(select[\s\w]*from)",
            r"(insert[\s\w]*into)",
            r"(delete[\s\w]*from)",
            r"(update[\s\w]*set)",
            r"(drop[\s\w]*table)",
            r"(create[\s\w]*table)",
            r"(alter[\s\w]*table)",
            r"(\bxp_cmdshell\b)",
            r"(\bsp_\w+\b)",
        ]
        
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.sql_injection_patterns]
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data for storage"""
        if not data:
            return ""
        
        try:
            encrypted = self.cipher.encrypt(data.encode())
            return encrypted.decode()
        except Exception as e:
            current_app.logger.error(f"Encryption error: {e}")
            raise
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data from storage"""
        if not encrypted_data:
            return ""
        
        try:
            decrypted = self.cipher.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception as e:
            current_app.logger.error(f"Decryption error: {e}")
            raise
    
    def validate_query_input(self, input_value: str, field_name: str = "input") -> Tuple[bool, str]:
        """Validate input for SQL injection attempts"""
        
        if not input_value:
            return True, ""
        
        # Check for SQL injection patterns
        for pattern in self.compiled_patterns:
            if pattern.search(input_value):
                SecurityAudit.log_security_event(
                    event_type=AuditEventType.SQL_INJECTION_ATTEMPT,
                    severity=AuditSeverity.HIGH,
                    success=False,
                    message=f"SQL injection attempt detected in {field_name}",
                    details={
                        'field': field_name,
                        'input_length': len(input_value),
                        'pattern_matched': pattern.pattern
                    }
                )
                return False, f"Invalid input detected in {field_name}"
        
        return True, ""
    
    def hash_password(self, password: str, salt: str = None) -> Tuple[str, str]:
        """Securely hash password with salt"""
        
        if salt is None:
            salt = secrets.token_hex(32)
        
        # Use PBKDF2 with high iteration count
        import hashlib
        import os
        
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 100,000 iterations
        )
        
        return key.hex(), salt
    
    def verify_password(self, password: str, hashed_password: str, salt: str) -> bool:
        """Verify password against hash"""
        
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        
        return key.hex() == hashed_password

class SecureQueryBuilder:
    """Build secure parameterized queries"""
    
    def __init__(self, db: SQLAlchemy):
        self.db = db
        self.db_security = DatabaseSecurity()
    
    def safe_execute(self, query: str, params: Dict = None, fetch_one: bool = False) -> Any:
        """Execute parameterized query safely"""
        
        try:
            # Validate all parameters
            if params:
                for key, value in params.items():
                    if isinstance(value, str):
                        is_valid, error = self.db_security.validate_query_input(value, key)
                        if not is_valid:
                            raise ValueError(f"Invalid parameter {key}: {error}")
            
            # Execute query with parameters
            result = self.db.session.execute(text(query), params or {})
            
            if fetch_one:
                return result.fetchone()
            else:
                return result.fetchall()
                
        except Exception as e:
            current_app.logger.error(f"Secure query execution error: {e}")
            raise
    
    def safe_select(self, table: str, columns: List[str], where_clause: str = None, 
                   params: Dict = None, limit: int = None) -> List:
        """Build and execute safe SELECT query"""
        
        # Validate table and column names (whitelist approach)
        if not self._is_safe_identifier(table):
            raise ValueError(f"Invalid table name: {table}")
        
        for column in columns:
            if not self._is_safe_identifier(column):
                raise ValueError(f"Invalid column name: {column}")
        
        # Build query
        query = f"SELECT {', '.join(columns)} FROM {table}"
        
        if where_clause:
            query += f" WHERE {where_clause}"
        
        if limit:
            query += f" LIMIT {int(limit)}"
        
        return self.safe_execute(query, params)
    
    def safe_insert(self, table: str, data: Dict) -> bool:
        """Build and execute safe INSERT query"""
        
        if not self._is_safe_identifier(table):
            raise ValueError(f"Invalid table name: {table}")
        
        # Validate all keys
        for key in data.keys():
            if not self._is_safe_identifier(key):
                raise ValueError(f"Invalid column name: {key}")
        
        # Build parameterized query
        columns = list(data.keys())
        placeholders = [f":{key}" for key in columns]
        
        query = f"""
        INSERT INTO {table} ({', '.join(columns)})
        VALUES ({', '.join(placeholders)})
        """
        
        try:
            self.safe_execute(query, data)
            self.db.session.commit()
            return True
        except Exception as e:
            self.db.session.rollback()
            current_app.logger.error(f"Safe insert error: {e}")
            return False
    
    def safe_update(self, table: str, data: Dict, where_clause: str, 
                   where_params: Dict = None) -> bool:
        """Build and execute safe UPDATE query"""
        
        if not self._is_safe_identifier(table):
            raise ValueError(f"Invalid table name: {table}")
        
        # Validate all keys
        for key in data.keys():
            if not self._is_safe_identifier(key):
                raise ValueError(f"Invalid column name: {key}")
        
        # Build SET clause
        set_clauses = [f"{key} = :{key}" for key in data.keys()]
        
        query = f"""
        UPDATE {table}
        SET {', '.join(set_clauses)}
        WHERE {where_clause}
        """
        
        # Combine parameters
        all_params = {**data}
        if where_params:
            all_params.update(where_params)
        
        try:
            self.safe_execute(query, all_params)
            self.db.session.commit()
            return True
        except Exception as e:
            self.db.session.rollback()
            current_app.logger.error(f"Safe update error: {e}")
            return False
    
    def _is_safe_identifier(self, identifier: str) -> bool:
        """Check if identifier is safe (alphanumeric and underscore only)"""
        return re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier) is not None

class DataEncryption:
    """Handle encryption of sensitive model fields"""
    
    def __init__(self, encryption_key: str = None):
        self.db_security = DatabaseSecurity(encryption_key)
    
    def encrypt_field(self, value: str) -> str:
        """Encrypt a field value"""
        return self.db_security.encrypt_sensitive_data(value)
    
    def decrypt_field(self, encrypted_value: str) -> str:
        """Decrypt a field value"""
        return self.db_security.decrypt_sensitive_data(encrypted_value)

# Decorators for secure database operations

def secure_db_operation(audit_operation: str = None):
    """Decorator to add security logging to database operations"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = datetime.utcnow()
            operation_success = False
            error_message = None
            
            try:
                result = f(*args, **kwargs)
                operation_success = True
                return result
                
            except Exception as e:
                error_message = str(e)
                current_app.logger.error(f"Database operation error in {f.__name__}: {e}")
                raise
                
            finally:
                # Log the operation
                if audit_operation:
                    duration = (datetime.utcnow() - start_time).total_seconds()
                    
                    SecurityAudit.log_security_event(
                        event_type=AuditEventType.DATA_ACCESS,
                        severity=AuditSeverity.LOW if operation_success else AuditSeverity.MEDIUM,
                        success=operation_success,
                        message=f"Database operation: {audit_operation}",
                        details={
                            'function': f.__name__,
                            'duration': duration,
                            'error': error_message
                        }
                    )
        
        return decorated_function
    return decorator

def validate_input_fields(**field_types):
    """Decorator to validate input fields before database operations"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            db_security = DatabaseSecurity()
            
            # Validate kwargs based on field types
            for field_name, field_type in field_types.items():
                if field_name in kwargs:
                    value = kwargs[field_name]
                    
                    if isinstance(value, str):
                        is_valid, error = db_security.validate_query_input(value, field_name)
                        if not is_valid:
                            raise ValueError(f"Invalid input for {field_name}: {error}")
                    
                    # Additional type-specific validation
                    if field_type == 'username':
                        if not SecurityValidator.validate_input(value, 'username')[0]:
                            raise ValueError(f"Invalid username format: {field_name}")
                    elif field_type == 'email':
                        if not SecurityValidator.validate_input(value, 'email')[0]:
                            raise ValueError(f"Invalid email format: {field_name}")
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

# SQLAlchemy event listeners for enhanced security

@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log SQL queries for security monitoring"""
    
    # Only log in development or if specifically enabled
    if current_app.config.get('LOG_SQL_QUERIES', False):
        # Sanitize statement for logging (remove sensitive data)
        sanitized_statement = re.sub(r"'[^']*'", "'***'", statement)
        current_app.logger.debug(f"SQL Query: {sanitized_statement}")

@event.listens_for(Pool, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set security-related SQLite pragmas"""
    
    if 'sqlite' in str(dbapi_connection):
        cursor = dbapi_connection.cursor()
        
        # Enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys=ON")
        
        # Set secure temp store
        cursor.execute("PRAGMA secure_delete=ON")
        
        # Set journal mode for better security
        cursor.execute("PRAGMA journal_mode=WAL")
        
        cursor.close()

# Database backup and security utilities

class DatabaseBackupSecurity:
    """Handle secure database backups"""
    
    def __init__(self, encryption_key: str = None):
        self.db_security = DatabaseSecurity(encryption_key)
    
    def create_encrypted_backup(self, backup_data: str, backup_name: str) -> str:
        """Create encrypted database backup"""
        
        try:
            # Encrypt backup data
            encrypted_backup = self.db_security.encrypt_sensitive_data(backup_data)
            
            # Generate backup metadata
            backup_metadata = {
                'name': backup_name,
                'created_at': datetime.utcnow().isoformat(),
                'checksum': hashlib.sha256(backup_data.encode()).hexdigest(),
                'encrypted': True
            }
            
            # Log backup creation
            SecurityAudit.log_security_event(
                event_type=AuditEventType.DATA_BACKUP,
                severity=AuditSeverity.LOW,
                success=True,
                message="Encrypted database backup created",
                details={'backup_name': backup_name}
            )
            
            return encrypted_backup
            
        except Exception as e:
            current_app.logger.error(f"Backup creation error: {e}")
            raise
    
    def verify_backup_integrity(self, backup_data: str, expected_checksum: str) -> bool:
        """Verify backup integrity"""
        
        try:
            # Decrypt backup if needed
            if self._is_encrypted_backup(backup_data):
                decrypted_data = self.db_security.decrypt_sensitive_data(backup_data)
            else:
                decrypted_data = backup_data
            
            # Calculate checksum
            actual_checksum = hashlib.sha256(decrypted_data.encode()).hexdigest()
            
            return actual_checksum == expected_checksum
            
        except Exception as e:
            current_app.logger.error(f"Backup verification error: {e}")
            return False
    
    def _is_encrypted_backup(self, backup_data: str) -> bool:
        """Check if backup data is encrypted"""
        try:
            self.db_security.decrypt_sensitive_data(backup_data)
            return True
        except:
            return False

# Connection security

class SecureConnectionManager:
    """Manage secure database connections"""
    
    @staticmethod
    def get_secure_connection_string(base_uri: str, ssl_mode: str = 'require') -> str:
        """Generate secure connection string"""
        
        if 'postgresql' in base_uri:
            # Add SSL parameters for PostgreSQL
            if '?' in base_uri:
                return f"{base_uri}&sslmode={ssl_mode}&sslcert=client-cert.pem&sslkey=client-key.pem&sslrootcert=ca-cert.pem"
            else:
                return f"{base_uri}?sslmode={ssl_mode}&sslcert=client-cert.pem&sslkey=client-key.pem&sslrootcert=ca-cert.pem"
        
        elif 'mysql' in base_uri:
            # Add SSL parameters for MySQL
            if '?' in base_uri:
                return f"{base_uri}&ssl_ca=ca-cert.pem&ssl_cert=client-cert.pem&ssl_key=client-key.pem"
            else:
                return f"{base_uri}?ssl_ca=ca-cert.pem&ssl_cert=client-cert.pem&ssl_key=client-key.pem"
        
        return base_uri
    
    @staticmethod
    def validate_connection_security(app):
        """Validate database connection security settings"""
        
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        
        security_issues = []
        
        # Check for SSL/TLS in production
        if app.config.get('ENV') == 'production':
            if 'postgresql' in db_uri and 'sslmode' not in db_uri:
                security_issues.append("PostgreSQL connection should use SSL in production")
            
            if 'mysql' in db_uri and 'ssl_ca' not in db_uri:
                security_issues.append("MySQL connection should use SSL in production")
        
        # Check for credentials in URI
        if '@' in db_uri and ('://' in db_uri):
            app.logger.warning("Database credentials detected in URI - consider using environment variables")
        
        return security_issues

# Initialize database security

def init_database_security(app, db):
    """Initialize database security features"""
    
    try:
        # Set up secure connection
        connection_manager = SecureConnectionManager()
        security_issues = connection_manager.validate_connection_security(app)
        
        for issue in security_issues:
            app.logger.warning(f"Database security issue: {issue}")
        
        # Initialize encryption
        encryption_key = app.config.get('DATABASE_ENCRYPTION_KEY')
        data_encryption = DataEncryption(encryption_key)
        
        # Set up query builder
        query_builder = SecureQueryBuilder(db)
        
        # Add to app context
        app.db_security = DatabaseSecurity(encryption_key)
        app.query_builder = query_builder
        app.data_encryption = data_encryption
        
        # Set up backup security
        backup_security = DatabaseBackupSecurity(encryption_key)
        app.backup_security = backup_security
        
        app.logger.info("Database security initialized successfully")
        
        return {
            'db_security': app.db_security,
            'query_builder': query_builder,
            'data_encryption': data_encryption,
            'backup_security': backup_security
        }
        
    except Exception as e:
        app.logger.error(f"Database security initialization failed: {e}")
        return None