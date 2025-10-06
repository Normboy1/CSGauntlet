"""
Secrets Management for CS Gauntlet
Secure handling of API keys, database credentials, and other sensitive configuration
"""

import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from flask import current_app
import redis

from .security import SecurityAudit
from .audit_logger import AuditEventType, AuditSeverity

class SecretsManager:
    """Centralized secrets management with encryption and rotation"""
    
    def __init__(self, master_key: str = None, redis_client=None):
        """Initialize secrets manager"""
        
        self.redis_client = redis_client
        self.secrets_prefix = "secrets:"
        self.vault_prefix = "vault:"
        
        # Initialize encryption
        if master_key:
            self.master_key = master_key.encode()
        else:
            self.master_key = self._generate_master_key()
        
        self.cipher = self._create_cipher(self.master_key)
        
        # Secret categories and their security levels
        self.secret_categories = {
            'database': {'rotation_days': 90, 'encryption_required': True},
            'api_keys': {'rotation_days': 30, 'encryption_required': True},
            'oauth': {'rotation_days': 180, 'encryption_required': True},
            'jwt': {'rotation_days': 7, 'encryption_required': True},
            'encryption': {'rotation_days': 365, 'encryption_required': True},
            'external_apis': {'rotation_days': 60, 'encryption_required': True}
        }
        
        # Environment-specific configurations
        self.environments = ['development', 'staging', 'production']
        self.current_env = os.getenv('FLASK_ENV', 'development')
    
    def _generate_master_key(self) -> bytes:
        """Generate master encryption key"""
        # In production, this should come from a secure key management service
        password = os.getenv('SECRETS_MASTER_PASSWORD', 'default-dev-password').encode()
        salt = os.getenv('SECRETS_SALT', 'default-salt').encode()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        return base64.urlsafe_b64encode(kdf.derive(password))
    
    def _create_cipher(self, key: bytes) -> Fernet:
        """Create encryption cipher"""
        return Fernet(key)
    
    def store_secret(self, category: str, name: str, value: str, 
                    environment: str = None, metadata: Dict = None) -> bool:
        """Store a secret securely"""
        
        try:
            environment = environment or self.current_env
            
            # Validate category
            if category not in self.secret_categories:
                raise ValueError(f"Invalid secret category: {category}")
            
            # Validate environment
            if environment not in self.environments:
                raise ValueError(f"Invalid environment: {environment}")
            
            # Create secret entry
            secret_data = {
                'name': name,
                'category': category,
                'environment': environment,
                'value': value,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'version': 1,
                'metadata': metadata or {},
                'rotation_due': self._calculate_rotation_date(category).isoformat(),
                'access_count': 0,
                'last_accessed': None
            }
            
            # Encrypt the secret
            encrypted_data = self._encrypt_secret_data(secret_data)
            
            # Store in Redis
            if self.redis_client:
                secret_key = f"{self.secrets_prefix}{environment}:{category}:{name}"
                
                # Store encrypted secret
                self.redis_client.set(secret_key, encrypted_data)
                
                # Add to category index
                category_key = f"{self.vault_prefix}category:{environment}:{category}"
                self.redis_client.sadd(category_key, name)
                
                # Add to environment index
                env_key = f"{self.vault_prefix}environment:{environment}"
                self.redis_client.sadd(env_key, f"{category}:{name}")
                
                # Set expiration for automatic cleanup (much longer than rotation)
                expiry_days = self.secret_categories[category]['rotation_days'] * 2
                self.redis_client.expire(secret_key, 86400 * expiry_days)
            
            # Log secret storage
            SecurityAudit.log_security_event(
                event_type=AuditEventType.SECRET_STORED,
                severity=AuditSeverity.MEDIUM,
                success=True,
                message=f"Secret stored: {category}/{name}",
                details={
                    'category': category,
                    'environment': environment,
                    'secret_name': name,
                    'has_metadata': bool(metadata)
                }
            )
            
            return True
            
        except Exception as e:
            current_app.logger.error(f"Secret storage error: {e}")
            SecurityAudit.log_security_event(
                event_type=AuditEventType.SECRET_STORAGE_FAILED,
                severity=AuditSeverity.HIGH,
                success=False,
                message=f"Failed to store secret: {category}/{name}",
                details={'error': str(e)}
            )
            return False
    
    def get_secret(self, category: str, name: str, environment: str = None) -> Optional[str]:
        """Retrieve a secret"""
        
        try:
            environment = environment or self.current_env
            
            if not self.redis_client:
                current_app.logger.warning("Redis not available for secrets retrieval")
                return None
            
            secret_key = f"{self.secrets_prefix}{environment}:{category}:{name}"
            encrypted_data = self.redis_client.get(secret_key)
            
            if not encrypted_data:
                return None
            
            # Decrypt secret
            secret_data = self._decrypt_secret_data(encrypted_data)
            
            # Update access tracking
            secret_data['access_count'] = secret_data.get('access_count', 0) + 1
            secret_data['last_accessed'] = datetime.utcnow().isoformat()
            
            # Re-encrypt and store updated data
            updated_encrypted = self._encrypt_secret_data(secret_data)
            self.redis_client.set(secret_key, updated_encrypted)
            
            return secret_data['value']
            
        except Exception as e:
            current_app.logger.error(f"Secret retrieval error: {e}")
            SecurityAudit.log_security_event(
                event_type=AuditEventType.SECRET_ACCESS_FAILED,
                severity=AuditSeverity.HIGH,
                success=False,
                message=f"Failed to retrieve secret: {category}/{name}",
                details={'error': str(e)}
            )
            return None
    
    def rotate_secret(self, category: str, name: str, new_value: str, 
                     environment: str = None) -> bool:
        """Rotate a secret to a new value"""
        
        try:
            environment = environment or self.current_env
            
            if not self.redis_client:
                return False
            
            secret_key = f"{self.secrets_prefix}{environment}:{category}:{name}"
            encrypted_data = self.redis_client.get(secret_key)
            
            if not encrypted_data:
                return False
            
            # Get current secret data
            secret_data = self._decrypt_secret_data(encrypted_data)
            
            # Update with new value
            secret_data['value'] = new_value
            secret_data['updated_at'] = datetime.utcnow().isoformat()
            secret_data['version'] = secret_data.get('version', 1) + 1
            secret_data['rotation_due'] = self._calculate_rotation_date(category).isoformat()
            
            # Store updated secret
            updated_encrypted = self._encrypt_secret_data(secret_data)
            self.redis_client.set(secret_key, updated_encrypted)
            
            # Log rotation
            SecurityAudit.log_security_event(
                event_type=AuditEventType.SECRET_ROTATED,
                severity=AuditSeverity.MEDIUM,
                success=True,
                message=f"Secret rotated: {category}/{name}",
                details={
                    'category': category,
                    'environment': environment,
                    'secret_name': name,
                    'new_version': secret_data['version']
                }
            )
            
            return True
            
        except Exception as e:
            current_app.logger.error(f"Secret rotation error: {e}")
            return False
    
    def delete_secret(self, category: str, name: str, environment: str = None) -> bool:
        """Delete a secret"""
        
        try:
            environment = environment or self.current_env
            
            if not self.redis_client:
                return False
            
            secret_key = f"{self.secrets_prefix}{environment}:{category}:{name}"
            
            # Remove from Redis
            deleted = self.redis_client.delete(secret_key)
            
            if deleted:
                # Remove from indexes
                category_key = f"{self.vault_prefix}category:{environment}:{category}"
                self.redis_client.srem(category_key, name)
                
                env_key = f"{self.vault_prefix}environment:{environment}"
                self.redis_client.srem(env_key, f"{category}:{name}")
                
                # Log deletion
                SecurityAudit.log_security_event(
                    event_type=AuditEventType.SECRET_DELETED,
                    severity=AuditSeverity.MEDIUM,
                    success=True,
                    message=f"Secret deleted: {category}/{name}",
                    details={
                        'category': category,
                        'environment': environment,
                        'secret_name': name
                    }
                )
                
                return True
            
            return False
            
        except Exception as e:
            current_app.logger.error(f"Secret deletion error: {e}")
            return False
    
    def list_secrets(self, category: str = None, environment: str = None) -> List[Dict]:
        """List secrets (metadata only, not values)"""
        
        try:
            environment = environment or self.current_env
            
            if not self.redis_client:
                return []
            
            secrets_list = []
            
            if category:
                # List secrets in specific category
                category_key = f"{self.vault_prefix}category:{environment}:{category}"
                secret_names = self.redis_client.smembers(category_key)
                
                for name in secret_names:
                    secret_key = f"{self.secrets_prefix}{environment}:{category}:{name.decode()}"
                    encrypted_data = self.redis_client.get(secret_key)
                    
                    if encrypted_data:
                        try:
                            secret_data = self._decrypt_secret_data(encrypted_data)
                            secrets_list.append({
                                'name': secret_data['name'],
                                'category': secret_data['category'],
                                'environment': secret_data['environment'],
                                'created_at': secret_data.get('created_at'),
                                'updated_at': secret_data.get('updated_at'),
                                'version': secret_data.get('version', 1),
                                'rotation_due': secret_data.get('rotation_due'),
                                'access_count': secret_data.get('access_count', 0),
                                'last_accessed': secret_data.get('last_accessed')
                            })
                        except:
                            continue
            else:
                # List all secrets in environment
                env_key = f"{self.vault_prefix}environment:{environment}"
                secret_refs = self.redis_client.smembers(env_key)
                
                for ref in secret_refs:
                    try:
                        cat, name = ref.decode().split(':', 1)
                        secret_key = f"{self.secrets_prefix}{environment}:{cat}:{name}"
                        encrypted_data = self.redis_client.get(secret_key)
                        
                        if encrypted_data:
                            secret_data = self._decrypt_secret_data(encrypted_data)
                            secrets_list.append({
                                'name': secret_data['name'],
                                'category': secret_data['category'],
                                'environment': secret_data['environment'],
                                'created_at': secret_data.get('created_at'),
                                'updated_at': secret_data.get('updated_at'),
                                'version': secret_data.get('version', 1),
                                'rotation_due': secret_data.get('rotation_due'),
                                'access_count': secret_data.get('access_count', 0),
                                'last_accessed': secret_data.get('last_accessed')
                            })
                    except:
                        continue
            
            return secrets_list
            
        except Exception as e:
            current_app.logger.error(f"List secrets error: {e}")
            return []
    
    def check_rotation_needed(self, environment: str = None) -> List[Dict]:
        """Check which secrets need rotation"""
        
        try:
            environment = environment or self.current_env
            secrets_needing_rotation = []
            
            all_secrets = self.list_secrets(environment=environment)
            current_time = datetime.utcnow()
            
            for secret in all_secrets:
                if secret.get('rotation_due'):
                    rotation_due = datetime.fromisoformat(secret['rotation_due'])
                    if current_time >= rotation_due:
                        secrets_needing_rotation.append(secret)
            
            return secrets_needing_rotation
            
        except Exception as e:
            current_app.logger.error(f"Rotation check error: {e}")
            return []
    
    def _encrypt_secret_data(self, secret_data: Dict) -> bytes:
        """Encrypt secret data"""
        json_data = json.dumps(secret_data)
        return self.cipher.encrypt(json_data.encode())
    
    def _decrypt_secret_data(self, encrypted_data: bytes) -> Dict:
        """Decrypt secret data"""
        if isinstance(encrypted_data, str):
            encrypted_data = encrypted_data.encode()
        
        decrypted_json = self.cipher.decrypt(encrypted_data)
        return json.loads(decrypted_json.decode())
    
    def _calculate_rotation_date(self, category: str) -> datetime:
        """Calculate when secret should be rotated"""
        rotation_days = self.secret_categories.get(category, {}).get('rotation_days', 30)
        return datetime.utcnow() + timedelta(days=rotation_days)

class ConfigurationManager:
    """Manages application configuration with secrets integration"""
    
    def __init__(self, secrets_manager: SecretsManager):
        self.secrets_manager = secrets_manager
        self.config_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
    def get_config_value(self, key: str, default: Any = None, 
                        secret_category: str = None) -> Any:
        """Get configuration value, potentially from secrets"""
        
        # Check cache first
        cache_key = f"{key}:{secret_category or 'env'}"
        if cache_key in self.config_cache:
            cache_entry = self.config_cache[cache_key]
            if datetime.utcnow() < cache_entry['expires']:
                return cache_entry['value']
        
        # Try environment variable first
        env_value = os.getenv(key)
        if env_value:
            # Cache environment value
            self.config_cache[cache_key] = {
                'value': env_value,
                'expires': datetime.utcnow() + timedelta(seconds=self.cache_ttl)
            }
            return env_value
        
        # Try secrets manager if category specified
        if secret_category:
            secret_value = self.secrets_manager.get_secret(secret_category, key.lower())
            if secret_value:
                # Cache secret value
                self.config_cache[cache_key] = {
                    'value': secret_value,
                    'expires': datetime.utcnow() + timedelta(seconds=self.cache_ttl)
                }
                return secret_value
        
        return default
    
    def set_config_secret(self, key: str, value: str, category: str) -> bool:
        """Store configuration value as secret"""
        return self.secrets_manager.store_secret(category, key.lower(), value)
    
    def clear_cache(self):
        """Clear configuration cache"""
        self.config_cache.clear()

class ProductionSecretsSetup:
    """Setup production secrets and configuration"""
    
    def __init__(self, secrets_manager: SecretsManager):
        self.secrets_manager = secrets_manager
    
    def initialize_production_secrets(self) -> bool:
        """Initialize all required production secrets"""
        
        try:
            # Database secrets
            self._setup_database_secrets()
            
            # JWT secrets
            self._setup_jwt_secrets()
            
            # OAuth secrets
            self._setup_oauth_secrets()
            
            # API secrets
            self._setup_api_secrets()
            
            # Encryption secrets
            self._setup_encryption_secrets()
            
            current_app.logger.info("Production secrets initialized successfully")
            return True
            
        except Exception as e:
            current_app.logger.error(f"Production secrets setup failed: {e}")
            return False
    
    def _setup_database_secrets(self):
        """Setup database-related secrets"""
        
        # Database encryption key
        if not self.secrets_manager.get_secret('database', 'encryption_key'):
            db_key = Fernet.generate_key().decode()
            self.secrets_manager.store_secret('database', 'encryption_key', db_key)
        
        # Database password (if not in environment)
        if not os.getenv('DATABASE_PASSWORD'):
            current_app.logger.warning("DATABASE_PASSWORD not set - should be configured")
    
    def _setup_jwt_secrets(self):
        """Setup JWT-related secrets"""
        
        # JWT secret key
        if not self.secrets_manager.get_secret('jwt', 'secret_key'):
            jwt_secret = secrets.token_urlsafe(64)
            self.secrets_manager.store_secret('jwt', 'secret_key', jwt_secret)
        
        # JWT refresh secret
        if not self.secrets_manager.get_secret('jwt', 'refresh_secret'):
            refresh_secret = secrets.token_urlsafe(64)
            self.secrets_manager.store_secret('jwt', 'refresh_secret', refresh_secret)
    
    def _setup_oauth_secrets(self):
        """Setup OAuth-related secrets"""
        
        # GitHub OAuth (if credentials provided)
        github_id = os.getenv('GITHUB_CLIENT_ID')
        github_secret = os.getenv('GITHUB_CLIENT_SECRET')
        
        if github_id and github_secret:
            self.secrets_manager.store_secret('oauth', 'github_client_id', github_id)
            self.secrets_manager.store_secret('oauth', 'github_client_secret', github_secret)
    
    def _setup_api_secrets(self):
        """Setup API-related secrets"""
        
        # OpenAI API key for AI grading
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            self.secrets_manager.store_secret('external_apis', 'openai_api_key', openai_key)
    
    def _setup_encryption_secrets(self):
        """Setup encryption-related secrets"""
        
        # Session encryption key
        if not self.secrets_manager.get_secret('encryption', 'session_key'):
            session_key = Fernet.generate_key().decode()
            self.secrets_manager.store_secret('encryption', 'session_key', session_key)

# Flask integration functions

def init_secrets_management(app, redis_client=None):
    """Initialize secrets management for the application"""
    
    try:
        # Create secrets manager
        master_key = app.config.get('SECRETS_MASTER_KEY')
        secrets_manager = SecretsManager(master_key, redis_client)
        
        # Create configuration manager
        config_manager = ConfigurationManager(secrets_manager)
        
        # Setup production secrets if in production
        if app.config.get('ENV') == 'production':
            prod_setup = ProductionSecretsSetup(secrets_manager)
            prod_setup.initialize_production_secrets()
        
        # Add to app
        app.secrets_manager = secrets_manager
        app.config_manager = config_manager
        
        # Helper function for getting secrets in views
        @app.context_processor
        def inject_secrets():
            return {
                'get_secret': lambda cat, name: secrets_manager.get_secret(cat, name),
                'get_config': lambda key, default=None, cat=None: config_manager.get_config_value(key, default, cat)
            }
        
        app.logger.info("Secrets management initialized successfully")
        
        return {
            'secrets_manager': secrets_manager,
            'config_manager': config_manager
        }
        
    except Exception as e:
        app.logger.error(f"Secrets management initialization failed: {e}")
        return None

def get_secret(category: str, name: str, default: str = None) -> str:
    """Helper function to get secret from current app"""
    try:
        if hasattr(current_app, 'secrets_manager'):
            value = current_app.secrets_manager.get_secret(category, name)
            return value if value is not None else default
        return default
    except:
        return default

def get_config(key: str, default: Any = None, secret_category: str = None) -> Any:
    """Helper function to get configuration value"""
    try:
        if hasattr(current_app, 'config_manager'):
            return current_app.config_manager.get_config_value(key, default, secret_category)
        return os.getenv(key, default)
    except:
        return default