from flask import Flask
from typing import Dict, Any, Optional
import os
import redis
from .security import SecurityValidator
from .rate_limiting import setup_rate_limiting
from .middleware import create_validation_middleware
from .cors_config import setup_secure_cors
from .security_headers import setup_security_headers
from .audit_logger import setup_audit_logging
from .secure_code_executor import SecureCodeExecutor
from .secure_upload import SecureFileUpload

class SecurityManager:
    """Central security configuration and management"""
    
    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        self.config = {}
        self.components = {}
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize all security components"""
        self.app = app
        self._load_security_config()
        self._setup_security_components()
        self._register_security_commands()
    
    def _load_security_config(self):
        """Load security configuration from environment and app config"""
        
        env = self.app.config.get('ENV', 'development')
        
        # Base security configuration
        self.config = {
            'environment': env,
            'debug_mode': self.app.config.get('DEBUG', False),
            
            # Rate limiting
            'rate_limiting': {
                'enabled': True,
                'redis_url': os.getenv('REDIS_URL', 'redis://localhost:6379'),
                'default_limits': ['1000 per hour', '100 per minute'],
                'strict_mode': env == 'production'
            },
            
            # CORS
            'cors': {
                'enabled': True,
                'strict_origins': env == 'production',
                'allow_credentials': True
            },
            
            # Security headers
            'headers': {
                'enabled': True,
                'csp_strict': env == 'production',
                'hsts_enabled': env == 'production'
            },
            
            # Audit logging
            'audit': {
                'enabled': True,
                'log_level': 'INFO' if env == 'production' else 'DEBUG',
                'log_dir': os.getenv('AUDIT_LOG_DIR', 'logs'),
                'buffer_size': 1000,
                'flush_interval': 60
            },
            
            # File uploads
            'uploads': {
                'enabled': True,
                'max_file_size': 10 * 1024 * 1024,  # 10MB
                'allowed_extensions': {
                    'images': ['jpg', 'jpeg', 'png', 'gif', 'webp'],
                    'documents': ['pdf', 'txt', 'md']
                },
                'virus_scanning': env == 'production'
            },
            
            # Code execution
            'code_execution': {
                'enabled': True,
                'sandbox_type': 'docker',  # 'docker' or 'native'
                'timeout': 10,
                'memory_limit': '128m',
                'docker_enabled': True
            },
            
            # Input validation
            'validation': {
                'enabled': True,
                'strict_mode': env == 'production',
                'sanitize_html': True,
                'max_input_length': {
                    'username': 50,
                    'email': 100,
                    'bio': 1000,
                    'code': 50000
                }
            },
            
            # Monitoring
            'monitoring': {
                'enabled': True,
                'alert_on_critical': env == 'production',
                'metrics_collection': True
            }
        }
        
        # Override with environment variables
        self._load_env_overrides()
    
    def _load_env_overrides(self):
        """Load configuration overrides from environment variables"""
        
        env_mappings = {
            'SECURITY_RATE_LIMITING_ENABLED': ('rate_limiting', 'enabled'),
            'SECURITY_CORS_ENABLED': ('cors', 'enabled'),
            'SECURITY_HEADERS_ENABLED': ('headers', 'enabled'),
            'SECURITY_AUDIT_ENABLED': ('audit', 'enabled'),
            'SECURITY_CODE_EXECUTION_TIMEOUT': ('code_execution', 'timeout'),
            'SECURITY_MAX_FILE_SIZE': ('uploads', 'max_file_size'),
        }
        
        for env_var, (section, key) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert string values to appropriate types
                if value.lower() in ('true', 'false'):
                    value = value.lower() == 'true'
                elif value.isdigit():
                    value = int(value)
                
                if section in self.config:
                    self.config[section][key] = value
    
    def _setup_security_components(self):
        """Initialize all security components"""
        
        # Setup Redis connection for rate limiting
        redis_client = None
        if self.config['rate_limiting']['enabled']:
            try:
                redis_client = redis.from_url(self.config['rate_limiting']['redis_url'])
                redis_client.ping()  # Test connection
            except Exception as e:
                self.app.logger.warning(f"Redis connection failed: {e}")
                redis_client = None
        
        # Rate limiting
        if self.config['rate_limiting']['enabled']:
            limiter = setup_rate_limiting(self.app, redis_client)
            self.components['limiter'] = limiter
        
        # Request validation middleware
        middleware = create_validation_middleware(self.app)
        self.components['middleware'] = middleware
        
        # CORS configuration
        if self.config['cors']['enabled']:
            cors_setup = setup_secure_cors(self.app)
            self.components['cors'] = cors_setup
        
        # Security headers
        if self.config['headers']['enabled']:
            headers_setup = setup_security_headers(self.app)
            self.components['headers'] = headers_setup
        
        # Audit logging
        if self.config['audit']['enabled']:
            audit_logger = setup_audit_logging(self.app)
            self.components['audit'] = audit_logger
        
        # Secure code executor
        if self.config['code_execution']['enabled']:
            code_executor = SecureCodeExecutor(
                timeout=self.config['code_execution']['timeout'],
                memory_limit=self.config['code_execution']['memory_limit']
            )
            self.components['code_executor'] = code_executor
        
        # Secure file upload
        if self.config['uploads']['enabled']:
            file_uploader = SecureFileUpload()
            self.components['file_uploader'] = file_uploader
        
        # Store security manager in app extensions
        if not hasattr(self.app, 'extensions'):
            self.app.extensions = {}
        self.app.extensions['security_manager'] = self
    
    def _register_security_commands(self):
        """Register Flask CLI commands for security management"""
        
        @self.app.cli.command('security-status')
        def security_status():
            """Show security configuration status"""
            click.echo("CS Gauntlet Security Status")
            click.echo("=" * 30)
            
            for component, status in self._get_security_status().items():
                status_icon = "✓" if status['enabled'] else "✗"
                click.echo(f"{status_icon} {component}: {status['status']}")
        
        @self.app.cli.command('security-test')
        def security_test():
            """Run security tests"""
            click.echo("Running security tests...")
            results = self._run_security_tests()
            
            for test, result in results.items():
                status_icon = "✓" if result['passed'] else "✗"
                click.echo(f"{status_icon} {test}: {result['message']}")
        
        @self.app.cli.command('generate-csp-report')
        def generate_csp_report():
            """Generate CSP violation report"""
            if 'audit' in self.components:
                audit_logger = self.components['audit']
                # Implementation would generate report from audit logs
                click.echo("CSP report generated (feature in development)")
            else:
                click.echo("Audit logging not enabled")
    
    def get_component(self, name: str):
        """Get a security component by name"""
        return self.components.get(name)
    
    def get_config(self, section: str = None, key: str = None):
        """Get security configuration"""
        if section is None:
            return self.config
        elif key is None:
            return self.config.get(section, {})
        else:
            return self.config.get(section, {}).get(key)
    
    def update_config(self, section: str, key: str, value: Any):
        """Update security configuration at runtime"""
        if section in self.config:
            self.config[section][key] = value
            
            # Apply configuration changes to components
            self._apply_config_changes(section, key, value)
    
    def _apply_config_changes(self, section: str, key: str, value: Any):
        """Apply configuration changes to running components"""
        
        if section == 'rate_limiting' and 'limiter' in self.components:
            # Update rate limiting configuration
            pass  # Implementation depends on specific rate limiter
        
        elif section == 'audit' and 'audit' in self.components:
            # Update audit logging configuration
            audit_logger = self.components['audit']
            if key == 'log_level':
                audit_logger._logger.setLevel(getattr(logging, value.upper()))
    
    def _get_security_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all security components"""
        
        status = {}
        
        for component_name, component in self.components.items():
            try:
                if component_name == 'limiter':
                    # Check rate limiter
                    status['Rate Limiting'] = {
                        'enabled': True,
                        'status': 'Active',
                        'details': f"Default limits: {self.config['rate_limiting']['default_limits']}"
                    }
                
                elif component_name == 'cors':
                    status['CORS'] = {
                        'enabled': True,
                        'status': 'Configured',
                        'details': f"Strict mode: {self.config['cors']['strict_origins']}"
                    }
                
                elif component_name == 'headers':
                    status['Security Headers'] = {
                        'enabled': True,
                        'status': 'Active',
                        'details': f"CSP strict: {self.config['headers']['csp_strict']}"
                    }
                
                elif component_name == 'audit':
                    status['Audit Logging'] = {
                        'enabled': True,
                        'status': 'Active',
                        'details': f"Log level: {self.config['audit']['log_level']}"
                    }
                
                elif component_name == 'code_executor':
                    status['Code Execution'] = {
                        'enabled': True,
                        'status': 'Active',
                        'details': f"Timeout: {self.config['code_execution']['timeout']}s"
                    }
                
                elif component_name == 'file_uploader':
                    status['File Upload'] = {
                        'enabled': True,
                        'status': 'Active',
                        'details': f"Max size: {self.config['uploads']['max_file_size']} bytes"
                    }
                
            except Exception as e:
                status[component_name] = {
                    'enabled': False,
                    'status': f'Error: {str(e)}',
                    'details': ''
                }
        
        return status
    
    def _run_security_tests(self) -> Dict[str, Dict[str, Any]]:
        """Run basic security tests"""
        
        tests = {}
        
        # Test input validation
        try:
            is_valid, _ = SecurityValidator.validate_input('test@example.com', 'email')
            tests['Input Validation'] = {
                'passed': is_valid,
                'message': 'Email validation working'
            }
        except Exception as e:
            tests['Input Validation'] = {
                'passed': False,
                'message': f'Error: {str(e)}'
            }
        
        # Test rate limiting
        if 'limiter' in self.components:
            tests['Rate Limiting'] = {
                'passed': True,
                'message': 'Rate limiter initialized'
            }
        else:
            tests['Rate Limiting'] = {
                'passed': False,
                'message': 'Rate limiter not available'
            }
        
        # Test audit logging
        if 'audit' in self.components:
            try:
                audit_logger = self.components['audit']
                audit_logger.log_event(
                    event_type=audit_logger.log_event.__defaults__[0],  # Use default event type
                    severity=audit_logger.log_event.__defaults__[1],    # Use default severity
                    success=True,
                    message="Security test event"
                )
                tests['Audit Logging'] = {
                    'passed': True,
                    'message': 'Audit logging functional'
                }
            except Exception as e:
                tests['Audit Logging'] = {
                    'passed': False,
                    'message': f'Error: {str(e)}'
                }
        else:
            tests['Audit Logging'] = {
                'passed': False,
                'message': 'Audit logging not available'
            }
        
        return tests
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """Get security metrics for monitoring"""
        
        metrics = {
            'timestamp': time.time(),
            'environment': self.config['environment'],
            'components_active': len(self.components),
            'security_events_24h': 0,  # Would be calculated from audit logs
            'failed_authentications_1h': 0,  # Would be calculated from audit logs
            'rate_limit_violations_1h': 0,  # Would be calculated from rate limiter
            'csp_violations_24h': 0,  # Would be calculated from CSP reports
        }
        
        # Add component-specific metrics
        if 'audit' in self.components:
            # Get recent security events count
            # This would require implementing a query method in audit logger
            pass
        
        return metrics

def create_security_manager(app: Flask) -> SecurityManager:
    """Factory function to create and configure security manager"""
    
    security_manager = SecurityManager(app)
    
    # Add security manager to app for easy access
    app.security = security_manager
    
    return security_manager

def get_security_manager(app: Flask = None) -> Optional[SecurityManager]:
    """Get the security manager instance"""
    
    if app is None:
        from flask import current_app
        app = current_app
    
    return app.extensions.get('security_manager')

# Security configuration validation
def validate_security_config(config: Dict[str, Any]) -> List[str]:
    """Validate security configuration and return list of issues"""
    
    issues = []
    
    # Check required sections
    required_sections = ['rate_limiting', 'cors', 'headers', 'audit']
    for section in required_sections:
        if section not in config:
            issues.append(f"Missing required section: {section}")
    
    # Validate rate limiting config
    if 'rate_limiting' in config:
        rl_config = config['rate_limiting']
        if rl_config.get('enabled', False) and not rl_config.get('redis_url'):
            issues.append("Rate limiting enabled but no Redis URL provided")
    
    # Validate upload config
    if 'uploads' in config:
        upload_config = config['uploads']
        max_size = upload_config.get('max_file_size', 0)
        if max_size > 100 * 1024 * 1024:  # 100MB
            issues.append(f"Max file size {max_size} bytes is very large")
    
    # Validate code execution config
    if 'code_execution' in config:
        code_config = config['code_execution']
        timeout = code_config.get('timeout', 0)
        if timeout > 60:  # 60 seconds
            issues.append(f"Code execution timeout {timeout}s is very high")
    
    return issues

# Import click for CLI commands
try:
    import click
except ImportError:
    click = None
    
import time
import logging