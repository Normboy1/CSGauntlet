# CS Gauntlet Security Implementation

This document describes the comprehensive security implementation for the CS Gauntlet competitive programming platform.

## Overview

The CS Gauntlet platform now includes enterprise-grade security features to protect against common web application vulnerabilities and ensure safe code execution in a competitive environment.

## Security Components

### 1. Input Validation and Sanitization (`security.py`)

**Features:**
- Pattern-based validation for usernames, emails, GitHub usernames, etc.
- HTML sanitization to prevent XSS attacks
- Code input validation with dangerous pattern detection
- Length limits and format validation

**Usage:**
```python
from backend.security import SecurityValidator

# Validate input
is_valid, error = SecurityValidator.validate_input('test@example.com', 'email')

# Sanitize HTML
clean_html = SecurityValidator.sanitize_html(user_content)

# Validate code
is_safe, sanitized = SecurityValidator.validate_code_input(code, 'python')
```

### 2. Rate Limiting (`rate_limiting.py`)

**Features:**
- Distributed rate limiting using Redis
- Adaptive limits based on user behavior
- Endpoint-specific rate limits
- Suspicious IP detection and stricter limits

**Configuration:**
```python
# Different limits for different operations
LIMITS = {
    'auth': {
        'login': "5 per minute",
        'register': "3 per minute"
    },
    'api': {
        'code_submission': "10 per minute"
    }
}
```

### 3. Secure Code Execution (`secure_code_executor.py`)

**Features:**
- Docker-based sandboxing with resource limits
- Code security validation before execution
- Dangerous pattern detection
- Timeout and memory limits
- User execution tracking

**Security Measures:**
- Read-only root filesystem
- Network disabled
- Capability dropping
- Process limits (max 20 processes)
- Memory limit (128MB default)
- CPU limits
- No root execution

### 4. File Upload Security (`secure_upload.py`)

**Features:**
- File type validation using magic numbers
- Virus scanning integration
- Image processing and EXIF stripping
- File size limits
- Malicious content detection

**Example:**
```python
from backend.secure_upload import upload_profile_photo

success, message, file_info = upload_profile_photo(file, user_id)
```

### 5. Request Validation Middleware (`middleware.py`)

**Features:**
- Comprehensive request validation
- Header security checks
- Path traversal protection
- Request size limits
- CSRF protection

### 6. CORS Security (`cors_config.py`)

**Features:**
- Environment-specific CORS policies
- Origin validation
- Suspicious origin detection
- Monitoring and logging

### 7. Security Headers (`security_headers.py`)

**Features:**
- Content Security Policy (CSP)
- HTTP Strict Transport Security (HSTS)
- X-Frame-Options, X-Content-Type-Options
- Permissions Policy
- CSP violation reporting

### 8. Audit Logging (`audit_logger.py`)

**Features:**
- Structured security event logging
- Real-time event processing
- Event categorization and severity levels
- Audit trail for compliance

### 9. Security Monitoring (`security_monitor.py`)

**Features:**
- Real-time threat detection
- Pattern-based alerting
- Security dashboard
- Automated incident response

## Installation

1. **Install Security Dependencies:**
```bash
pip install -r requirements_security.txt
```

2. **Install Optional Dependencies:**
```bash
# For enhanced file security
pip install python-magic python-magic-bin

# For development security tools
pip install bandit safety
```

3. **Setup Redis (Required for Rate Limiting):**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# Windows
# Download from https://redis.io/download
```

4. **Setup Docker (Required for Secure Code Execution):**
```bash
# Install Docker Desktop from https://docker.com
# Ensure Docker daemon is running
```

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Security Configuration
SECURITY_RATE_LIMITING_ENABLED=true
SECURITY_CORS_ENABLED=true
SECURITY_HEADERS_ENABLED=true
SECURITY_AUDIT_ENABLED=true
SECURITY_CODE_EXECUTION_TIMEOUT=10
SECURITY_MAX_FILE_SIZE=10485760

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Audit Logging
AUDIT_LOG_DIR=logs

# Code Execution
DOCKER_ENABLED=true
CODE_EXECUTION_MEMORY_LIMIT=128m
```

### Flask App Integration

Replace your existing app creation with the secure version:

```python
# Old way
from backend import create_app

# New way
from backend.secure_app import create_secure_app

app = create_secure_app(ProductionConfig)
```

### Manual Integration (if needed)

```python
from flask import Flask
from backend.security_config import create_security_manager

app = Flask(__name__)
security_manager = create_security_manager(app)
```

## Usage Examples

### 1. Protecting Routes with Validation

```python
from backend.middleware import validate_code_submission, validate_profile_update

@app.route('/api/submit_code', methods=['POST'])
@validate_code_submission
def submit_code():
    # g.validated_data contains sanitized input
    code = g.validated_data['code']
    # ... rest of function
```

### 2. Secure Code Execution

```python
from backend.secure_code_executor import SecureCodeExecutor

executor = SecureCodeExecutor()
success, message, results, grading = await executor.execute_and_grade_securely(
    code=user_code,
    test_cases=problem_tests,
    problem_description=problem_desc,
    user_id=str(current_user.id)
)
```

### 3. Rate Limiting Specific Endpoints

```python
from backend.rate_limiting import code_execution_rate_limit

@app.route('/api/execute_code', methods=['POST'])
@code_execution_rate_limit
def execute_code():
    # Limited to 10 executions per minute per user
    pass
```

### 4. Audit Logging

```python
from backend.audit_logger import audit_login, audit_data_access

@app.route('/login', methods=['POST'])
@audit_login
def login():
    # Login attempts are automatically logged
    pass

@app.route('/api/sensitive_data')
@audit_data_access('access')
def get_sensitive_data():
    # Data access is automatically logged
    pass
```

## Security Monitoring

### Dashboard Access

The security dashboard is available at:
- Development: `http://localhost:5000/admin/security/`
- Production: `https://yourdomain.com/admin/security/`

**Note:** Requires admin privileges (implement `is_admin` property on User model)

### Real-time Monitoring

The system monitors for:
- Failed login attempts
- Suspicious code execution
- Rate limit violations
- File upload attacks
- CORS violations
- Privilege escalation attempts

### Alert Levels

- **LOW**: Normal security events, routine monitoring
- **MEDIUM**: Unusual activity requiring attention
- **HIGH**: Potential security threats requiring immediate review
- **CRITICAL**: Active security incidents requiring immediate response

## CLI Commands

```bash
# Check security status
flask security-status

# Run security tests
flask security-test

# Initialize security configuration
flask init-security

# Run security audit
flask security-audit
```

## Security Best Practices

### 1. Environment Configuration

**Production:**
- Use HTTPS only
- Set secure session cookies
- Enable strict CSP
- Use strong secrets
- Enable all security headers

**Development:**
- More permissive CORS for local development
- Relaxed CSP for debugging
- Debug mode for detailed error messages

### 2. Code Execution Security

- Never trust user code
- Always run in sandboxed environment
- Monitor resource usage
- Log all execution attempts
- Validate code before execution

### 3. File Upload Security

- Validate file types using magic numbers
- Scan for malicious content
- Limit file sizes
- Process images to remove metadata
- Store files outside web root

### 4. Authentication & Authorization

- Use strong password hashing (bcrypt)
- Implement rate limiting on auth endpoints
- Log all authentication events
- Use secure session management
- Implement proper CSRF protection

## Threat Detection

### Automated Detection

The system automatically detects:

1. **Brute Force Attacks**: Multiple failed login attempts
2. **Code Injection**: Dangerous patterns in submitted code
3. **File Upload Attacks**: Malicious files or excessive uploads
4. **Rate Limit Abuse**: Excessive API requests
5. **CORS Violations**: Unauthorized cross-origin requests
6. **Privilege Escalation**: Unauthorized access attempts

### Response Actions

When threats are detected:

1. **Immediate**: Block dangerous requests
2. **Short-term**: Rate limit suspicious IPs
3. **Long-term**: Blacklist persistent attackers
4. **Alerting**: Notify administrators of critical threats

## Compliance & Auditing

### Audit Trail

All security events are logged with:
- Timestamp
- User ID
- IP address
- Event type and severity
- Detailed context
- Request correlation ID

### Log Retention

- Security logs are rotated automatically
- 10MB max file size with 10 backup files
- Structured JSON format for analysis
- Integration ready for SIEM systems

### Compliance Features

- GDPR: Personal data handling and audit trails
- SOC 2: Security controls and monitoring
- OWASP: Protection against Top 10 vulnerabilities

## Troubleshooting

### Common Issues

1. **Redis Connection Errors**
   ```bash
   # Check Redis status
   redis-cli ping
   
   # Start Redis
   redis-server
   ```

2. **Docker Permission Issues**
   ```bash
   # Add user to docker group (Linux)
   sudo usermod -aG docker $USER
   
   # Restart session or run:
   newgrp docker
   ```

3. **File Upload Failures**
   ```bash
   # Install python-magic
   pip install python-magic python-magic-bin
   
   # On macOS
   brew install libmagic
   ```

4. **CSP Violations**
   - Check browser console for CSP errors
   - Adjust CSP policy in `security_headers.py`
   - Use CSP report endpoint for debugging

### Performance Considerations

- Redis is used for rate limiting - ensure adequate memory
- Docker containers are created per code execution - monitor disk space
- Audit logs can grow large - implement log rotation
- Security middleware adds ~1-5ms per request

### Monitoring

- Check `/admin/security/dashboard` for security metrics
- Monitor Redis memory usage
- Watch Docker container creation/destruction
- Review audit logs regularly

## Security Updates

### Regular Maintenance

1. Update security dependencies monthly:
   ```bash
   pip install -U -r requirements_security.txt
   ```

2. Run security scans:
   ```bash
   bandit -r backend/
   safety check
   ```

3. Review audit logs weekly
4. Update threat detection patterns based on new threats
5. Test security controls quarterly

### Incident Response

1. **Detection**: Automated alerts or manual discovery
2. **Assessment**: Determine threat level and impact
3. **Containment**: Block threats, isolate affected systems
4. **Investigation**: Analyze logs, determine root cause
5. **Recovery**: Restore normal operations
6. **Lessons Learned**: Update security controls

## Contributing

When adding new security features:

1. Follow principle of least privilege
2. Add comprehensive logging
3. Include input validation
4. Add rate limiting if applicable
5. Update threat detection patterns
6. Document security implications
7. Add security tests

## Security Contact

For security issues:
- Create GitHub issue with "security" label
- Email: security@csgatuntlet.com (if configured)
- Follow responsible disclosure principles

## Legal

This security implementation is provided as-is. Users are responsible for:
- Compliance with applicable laws
- Regular security updates
- Proper configuration for their environment
- Incident response procedures

---

**Last Updated:** 2024-01-15
**Version:** 1.0.0
**Security Level:** Enterprise Grade