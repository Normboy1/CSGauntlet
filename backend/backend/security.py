import re
import html
import bleach
import secrets
import hashlib
import os
import time
from functools import wraps
from flask import request, jsonify, current_app, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import ipaddress
import subprocess
import tempfile
import shutil
from pathlib import Path

class SecurityValidator:
    """Comprehensive input validation and sanitization utilities"""
    
    # Common patterns for validation
    PATTERNS = {
        'username': re.compile(r'^[a-zA-Z0-9_]{3,20}$'),
        'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
        'github_username': re.compile(r'^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$'),
        'college_name': re.compile(r'^[a-zA-Z0-9\s\-\.]{2,100}$'),
        'uuid': re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        'language': re.compile(r'^(python|javascript|java|cpp|c|go|rust|php|ruby|swift|kotlin)$'),
        'difficulty': re.compile(r'^(easy|medium|hard)$'),
        'game_mode': re.compile(r'^(casual|ranked|custom|trivia|debug)$')
    }
    
    # Allowed HTML tags for rich text content
    ALLOWED_HTML_TAGS = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li', 'a', 'code', 'pre']
    ALLOWED_HTML_ATTRIBUTES = {'a': ['href', 'title'], 'img': ['src', 'alt']}
    
    @staticmethod
    def validate_input(value, field_type, required=True, max_length=None):
        """Validate input against predefined patterns"""
        if not value and required:
            return False, f"{field_type} is required"
        
        if not value and not required:
            return True, None
            
        if isinstance(value, str):
            value = value.strip()
            
        if max_length and len(str(value)) > max_length:
            return False, f"{field_type} exceeds maximum length of {max_length}"
            
        if field_type in SecurityValidator.PATTERNS:
            if not SecurityValidator.PATTERNS[field_type].match(str(value)):
                return False, f"Invalid {field_type} format"
                
        return True, None
    
    @staticmethod
    def sanitize_html(content):
        """Sanitize HTML content to prevent XSS"""
        if not content:
            return ""
        return bleach.clean(
            content,
            tags=SecurityValidator.ALLOWED_HTML_TAGS,
            attributes=SecurityValidator.ALLOWED_HTML_ATTRIBUTES,
            strip=True
        )
    
    @staticmethod
    def sanitize_text(text, max_length=1000):
        """Sanitize plain text input"""
        if not text:
            return ""
        
        # Remove control characters except newlines and tabs
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Limit length
        if len(text) > max_length:
            text = text[:max_length]
            
        # HTML escape
        return html.escape(text.strip())
    
    @staticmethod
    def validate_code_input(code, language="python", max_length=50000):
        """Validate and sanitize code input"""
        if not code:
            return False, "Code cannot be empty"
            
        if len(code) > max_length:
            return False, f"Code exceeds maximum length of {max_length} characters"
        
        # Check for potentially dangerous patterns
        dangerous_patterns = [
            r'import\s+os',
            r'import\s+subprocess',
            r'import\s+sys',
            r'__import__',
            r'eval\s*\(',
            r'exec\s*\(',
            r'compile\s*\(',
            r'open\s*\(',
            r'file\s*\(',
            r'input\s*\(',
            r'raw_input\s*\(',
            r'__.*__',  # dunder methods
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                current_app.logger.warning(f"Dangerous code pattern detected: {pattern}")
        
        return True, SecurityValidator.sanitize_text(code, max_length)

class FileSecurityValidator:
    """Secure file upload validation"""
    
    ALLOWED_EXTENSIONS = {
        'image': {'png', 'jpg', 'jpeg', 'gif', 'webp'},
        'document': {'pdf', 'txt', 'md'},
        'code': {'py', 'js', 'java', 'cpp', 'c', 'go', 'rs', 'php', 'rb'}
    }
    
    MAX_FILE_SIZES = {
        'image': 5 * 1024 * 1024,  # 5MB
        'document': 10 * 1024 * 1024,  # 10MB
        'code': 1 * 1024 * 1024,  # 1MB
    }
    
    DANGEROUS_MIME_TYPES = {
        'application/x-executable',
        'application/x-msdownload',
        'application/x-msdos-program',
        'application/x-msi',
        'application/x-bat',
        'application/x-sh',
        'text/x-shellscript'
    }
    
    @staticmethod
    def validate_file(file, file_type='image'):
        """Comprehensive file validation"""
        if not file or not file.filename:
            return False, "No file provided"
        
        filename = secure_filename(file.filename)
        if not filename:
            return False, "Invalid filename"
        
        # Check file extension
        ext = filename.rsplit('.', 1)[-1].lower()
        if ext not in FileSecurityValidator.ALLOWED_EXTENSIONS.get(file_type, set()):
            return False, f"File type .{ext} not allowed for {file_type}"
        
        # Check file size
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        
        max_size = FileSecurityValidator.MAX_FILE_SIZES.get(file_type, 1024*1024)
        if size > max_size:
            return False, f"File size {size} exceeds maximum {max_size} bytes"
        
        # Check MIME type
        import magic
        try:
            mime_type = magic.from_buffer(file.read(1024), mime=True)
            file.seek(0)
            
            if mime_type in FileSecurityValidator.DANGEROUS_MIME_TYPES:
                return False, f"Dangerous MIME type: {mime_type}"
        except:
            pass  # magic library might not be available
        
        return True, filename
    
    @staticmethod
    def scan_file_content(filepath):
        """Scan file for malicious content"""
        try:
            with open(filepath, 'rb') as f:
                content = f.read(8192)  # Read first 8KB
                
            # Check for common malware signatures
            dangerous_signatures = [
                b'MZ',  # PE executable
                b'\x7fELF',  # ELF executable
                b'#!/bin/sh',
                b'#!/bin/bash',
                b'<script',
                b'javascript:',
                b'vbscript:',
            ]
            
            for sig in dangerous_signatures:
                if sig in content:
                    return False, f"Dangerous content detected"
            
            return True, "File content appears safe"
        except Exception as e:
            return False, f"Error scanning file: {str(e)}"

class CodeSandbox:
    """Secure code execution sandbox"""
    
    def __init__(self):
        self.temp_dir = None
        self.allowed_imports = {
            'python': ['math', 'random', 'collections', 'itertools', 'functools', 'operator', 'string'],
            'javascript': ['Math', 'JSON', 'Array', 'Object', 'String', 'Number'],
        }
    
    def create_sandbox(self):
        """Create a temporary isolated directory"""
        self.temp_dir = tempfile.mkdtemp(prefix='cs_gauntlet_sandbox_')
        return self.temp_dir
    
    def cleanup_sandbox(self):
        """Clean up the sandbox directory"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def validate_code_safety(self, code, language):
        """Validate code for security issues before execution"""
        dangerous_patterns = {
            'python': [
                r'import\s+(os|sys|subprocess|socket|urllib|requests|http)',
                r'__import__\s*\(',
                r'eval\s*\(',
                r'exec\s*\(',
                r'compile\s*\(',
                r'open\s*\(',
                r'file\s*\(',
                r'input\s*\(',
                r'raw_input\s*\(',
                r'globals\s*\(',
                r'locals\s*\(',
                r'vars\s*\(',
                r'dir\s*\(',
                r'getattr\s*\(',
                r'setattr\s*\(',
                r'hasattr\s*\(',
                r'delattr\s*\(',
                r'while\s+True\s*:',  # Infinite loops
                r'for\s+.*\s+in\s+range\s*\(\s*\d{6,}',  # Large loops
            ],
            'javascript': [
                r'require\s*\(',
                r'import\s+.*\s+from',
                r'eval\s*\(',
                r'Function\s*\(',
                r'setTimeout\s*\(',
                r'setInterval\s*\(',
                r'XMLHttpRequest',
                r'fetch\s*\(',
                r'while\s*\(\s*true\s*\)',
                r'for\s*\(\s*;\s*;\s*\)',
            ]
        }
        
        patterns = dangerous_patterns.get(language, [])
        violations = []
        
        for pattern in patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                violations.append(f"Dangerous pattern detected: {match.group()}")
        
        return len(violations) == 0, violations
    
    def execute_code_safely(self, code, language, timeout=10):
        """Execute code in a secure sandbox with timeout"""
        if not self.temp_dir:
            self.create_sandbox()
        
        is_safe, violations = self.validate_code_safety(code, language)
        if not is_safe:
            return False, f"Security violations: {'; '.join(violations)}", None
        
        try:
            if language == 'python':
                return self._execute_python(code, timeout)
            elif language == 'javascript':
                return self._execute_javascript(code, timeout)
            else:
                return False, f"Language {language} not supported", None
        finally:
            self.cleanup_sandbox()
    
    def _execute_python(self, code, timeout):
        """Execute Python code safely"""
        code_file = os.path.join(self.temp_dir, 'solution.py')
        
        # Prepend safety restrictions
        safe_code = f"""
import sys
import signal

# Limit execution time
def timeout_handler(signum, frame):
    raise TimeoutError("Code execution timed out")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm({timeout})

try:
{chr(10).join('    ' + line for line in code.split(chr(10)))}
except TimeoutError as e:
    print(f"ERROR: {{e}}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {{e}}")
    sys.exit(1)
finally:
    signal.alarm(0)
"""
        
        with open(code_file, 'w') as f:
            f.write(safe_code)
        
        try:
            result = subprocess.run([
                'python', code_file
            ], 
            capture_output=True, 
            text=True, 
            timeout=timeout + 2,
            cwd=self.temp_dir
            )
            
            if result.returncode == 0:
                return True, "Execution successful", result.stdout
            else:
                return False, f"Execution failed: {result.stderr}", result.stdout
                
        except subprocess.TimeoutExpired:
            return False, "Code execution timed out", None
        except Exception as e:
            return False, f"Execution error: {str(e)}", None
    
    def _execute_javascript(self, code, timeout):
        """Execute JavaScript code safely using Node.js"""
        code_file = os.path.join(self.temp_dir, 'solution.js')
        
        # Prepend safety restrictions
        safe_code = f"""
// Disable dangerous globals
delete global.require;
delete global.process;
delete global.__dirname;
delete global.__filename;

// Set timeout
setTimeout(() => {{
    console.error("ERROR: Code execution timed out");
    process.exit(1);
}}, {timeout * 1000});

try {{
{code}
}} catch (error) {{
    console.error("ERROR:", error.message);
    process.exit(1);
}}
"""
        
        with open(code_file, 'w') as f:
            f.write(safe_code)
        
        try:
            result = subprocess.run([
                'node', '--no-experimental-modules', code_file
            ], 
            capture_output=True, 
            text=True, 
            timeout=timeout + 2,
            cwd=self.temp_dir
            )
            
            if result.returncode == 0:
                return True, "Execution successful", result.stdout
            else:
                return False, f"Execution failed: {result.stderr}", result.stdout
                
        except subprocess.TimeoutExpired:
            return False, "Code execution timed out", None
        except Exception as e:
            return False, f"Execution error: {str(e)}", None

class SecurityAudit:
    """Security audit logging and monitoring"""
    
    @staticmethod
    def log_security_event(event_type, user_id=None, ip_address=None, details=None):
        """Log security-related events"""
        timestamp = datetime.utcnow()
        
        log_entry = {
            'timestamp': timestamp.isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'ip_address': ip_address or request.remote_addr if request else None,
            'user_agent': request.headers.get('User-Agent') if request else None,
            'details': details
        }
        
        # Log to application logger
        current_app.logger.warning(f"SECURITY_EVENT: {log_entry}")
        
        # In production, you might want to send to SIEM or security monitoring system
        return log_entry
    
    @staticmethod
    def detect_suspicious_activity(user_id, activity_type):
        """Detect patterns of suspicious activity"""
        # This could be enhanced with Redis or database tracking
        # For now, just log the activity
        SecurityAudit.log_security_event(
            'suspicious_activity_detected',
            user_id=user_id,
            details={'activity_type': activity_type}
        )

def require_security_headers(f):
    """Decorator to add security headers"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = f(*args, **kwargs)
        
        # Add security headers
        if hasattr(response, 'headers'):
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
        return response
    return decorated_function

def validate_request_data(schema):
    """Decorator to validate request data against a schema"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.is_json:
                data = request.get_json()
            else:
                data = request.form.to_dict()
                
            # Validate against schema
            for field, rules in schema.items():
                value = data.get(field)
                
                if rules.get('required', False) and not value:
                    return jsonify({'error': f'{field} is required'}), 400
                
                if value and 'type' in rules:
                    field_type = rules['type']
                    max_length = rules.get('max_length')
                    
                    is_valid, error_msg = SecurityValidator.validate_input(
                        value, field_type, rules.get('required', False), max_length
                    )
                    
                    if not is_valid:
                        return jsonify({'error': error_msg}), 400
                    
                    # Sanitize the value
                    if isinstance(value, str):
                        data[field] = SecurityValidator.sanitize_text(value, max_length)
            
            # Store validated data in request context
            g.validated_data = data
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Rate limiting setup
def create_limiter(app):
    """Create and configure rate limiter"""
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["1000 per hour"]
    )
    return limiter

# Common validation schemas
VALIDATION_SCHEMAS = {
    'user_profile': {
        'username': {'type': 'username', 'required': True, 'max_length': 20},
        'email': {'type': 'email', 'required': True, 'max_length': 100},
        'college_name': {'type': 'college_name', 'required': False, 'max_length': 100},
        'github_username': {'type': 'github_username', 'required': False, 'max_length': 39},
        'bio': {'type': 'text', 'required': False, 'max_length': 500}
    },
    'code_submission': {
        'code': {'type': 'text', 'required': True, 'max_length': 50000},
        'language': {'type': 'language', 'required': True},
        'problem_id': {'type': 'text', 'required': True, 'max_length': 50}
    },
    'game_settings': {
        'game_mode': {'type': 'game_mode', 'required': True},
        'difficulty': {'type': 'difficulty', 'required': False}
    }
}