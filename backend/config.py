import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///cs_gauntlet.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SOCKET_URL = os.environ.get('SOCKET_URL', 'http://localhost:5001')
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID', '')
    GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET', '')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # AI Grader Configuration
    AI_PROVIDER = os.getenv('AI_PROVIDER', 'ollama')
    OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'codellama:7b')
    
    # Security Configuration
    RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'True').lower() == 'true'
    RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', '60'))
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', '16777216'))  # 16MB
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'static/uploads')
    
    # Docker Configuration
    DOCKER_TIMEOUT = int(os.getenv('DOCKER_TIMEOUT', '10'))
    DOCKER_MEMORY_LIMIT = os.getenv('DOCKER_MEMORY_LIMIT', '256m')
    DOCKER_IMAGE = os.getenv('DOCKER_IMAGE', 'python:3.9-slim')
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/cs_gauntlet.log')
    
    # CORS Configuration
    CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:5173')
    
    # Celery Configuration
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = True

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    REDIS_URL = 'redis://localhost:6379/1'

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'