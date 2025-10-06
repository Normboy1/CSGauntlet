#!/usr/bin/env python3
"""
CS Gauntlet Production Deployment Script
Deploy to various cloud platforms with Ollama AI Grader
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def print_banner():
    """Print deployment banner"""
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                🚀 CS GAUNTLET DEPLOYMENT 🚀               ║
    ║              Production Ready with Ollama AI             ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

def generate_production_env():
    """Generate production environment variables"""
    print("🔧 Generating production environment configuration...")
    
    import secrets
    from cryptography.fernet import Fernet
    
    # Generate secure keys
    secret_key = secrets.token_urlsafe(64)
    jwt_secret = secrets.token_urlsafe(64)
    db_encryption_key = Fernet.generate_key().decode()
    
    prod_env = f"""# CS Gauntlet Production Environment
# Generated on {os.popen('date').read().strip()}

# Flask Configuration
SECRET_KEY={secret_key}
JWT_SECRET_KEY={jwt_secret}
FLASK_ENV=production

# Database Configuration (Update with your production database)
DATABASE_URL=postgresql://user:password@host:port/cs_gauntlet
DATABASE_ENCRYPTION_KEY={db_encryption_key}

# Redis Configuration (Update with your production Redis)
REDIS_URL=redis://host:port/0

# AI Grader Configuration
AI_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=codellama:7b

# OpenAI Fallback (Optional)
OPENAI_API_KEY=your-openai-api-key

# GitHub OAuth (Optional but recommended)
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# Security Configuration
FORCE_HTTPS=true
SESSION_COOKIE_SECURE=true
REMEMBER_COOKIE_SECURE=true

# CORS Configuration (Update with your domain)
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
"""
    
    with open('production.env', 'w') as f:
        f.write(prod_env)
    
    print("✅ Production environment file created: production.env")
    print("⚠️  Please update database URLs and domain names before deploying!")
    return True

def create_dockerfile():
    """Create production Dockerfile"""
    print("🐳 Creating production Dockerfile...")
    
    dockerfile_content = """# CS Gauntlet Production Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    curl \\
    redis-tools \\
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for frontend build
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \\
    && apt-get install -y nodejs

# Copy backend requirements and install Python dependencies
COPY backend/requirements.txt /app/backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy frontend package.json and install Node dependencies
COPY frontend/package*.json /app/frontend/
RUN cd frontend && npm ci

# Copy application code
COPY . /app/

# Build frontend
RUN cd frontend && npm run build

# Create logs directory
RUN mkdir -p /app/backend/logs

# Expose port
EXPOSE 5001

# Set environment variables
ENV FLASK_ENV=production
ENV PYTHONPATH=/app/backend

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD curl -f http://localhost:5001/health || exit 1

# Start command
CMD ["python", "/app/backend/run_enhanced.py"]
"""
    
    with open('Dockerfile', 'w') as f:
        f.write(dockerfile_content)
    
    print("✅ Dockerfile created")
    return True

def create_docker_compose():
    """Create docker-compose for production"""
    print("🐳 Creating docker-compose.yml...")
    
    compose_content = """version: '3.8'

services:
  cs-gauntlet:
    build: .
    ports:
      - "5001:5001"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://postgres:password@db:5432/cs_gauntlet
      - REDIS_URL=redis://redis:6379/0
      - OLLAMA_URL=http://ollama:11434
    depends_on:
      - db
      - redis
      - ollama
    volumes:
      - ./backend/logs:/app/backend/logs
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: cs_gauntlet
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped
    command: ["ollama", "serve"]

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - cs-gauntlet
    restart: unless-stopped

volumes:
  postgres_data:
  ollama_data:
"""
    
    with open('docker-compose.yml', 'w') as f:
        f.write(compose_content)
    
    print("✅ docker-compose.yml created")
    return True

def create_nginx_config():
    """Create Nginx configuration"""
    print("🌐 Creating Nginx configuration...")
    
    nginx_content = """events {
    worker_connections 1024;
}

http {
    upstream cs_gauntlet {
        server cs-gauntlet:5001;
    }

    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;
        
        # Redirect HTTP to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        # SSL Configuration (update with your certificates)
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

        # WebSocket support
        location /socket.io/ {
            proxy_pass http://cs_gauntlet;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # API and backend routes
        location /api/ {
            proxy_pass http://cs_gauntlet;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Static files and frontend
        location / {
            proxy_pass http://cs_gauntlet;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
"""
    
    with open('nginx.conf', 'w') as f:
        f.write(nginx_content)
    
    print("✅ nginx.conf created")
    print("⚠️  Update server_name and SSL certificate paths!")
    return True

def create_deployment_guide():
    """Create deployment guide"""
    print("📖 Creating deployment guide...")
    
    guide_content = """# CS Gauntlet Production Deployment Guide

## Quick Deploy Options

### Option 1: Docker Compose (Recommended)
```bash
# 1. Update production.env with your configuration
# 2. Update nginx.conf with your domain
# 3. Add SSL certificates to ./ssl/ directory
# 4. Deploy
docker-compose up -d

# Pull Ollama model
docker exec cs-gauntlet-ollama-1 ollama pull codellama:7b
```

### Option 2: Railway
```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login and deploy
railway login
railway init
railway up
```

### Option 3: Heroku
```bash
# 1. Create Heroku app
heroku create your-cs-gauntlet-app

# 2. Add PostgreSQL and Redis
heroku addons:create heroku-postgresql:mini
heroku addons:create heroku-redis:mini

# 3. Set environment variables
heroku config:set FLASK_ENV=production
heroku config:set SECRET_KEY=your-secret-key
# ... (add all production.env variables)

# 4. Deploy
git push heroku main
```

### Option 4: DigitalOcean App Platform
```bash
# 1. Create app.yaml configuration
# 2. Connect GitHub repository
# 3. Deploy via DigitalOcean dashboard
```

## Environment Variables Required

Copy from production.env and update:
- DATABASE_URL (PostgreSQL connection string)
- REDIS_URL (Redis connection string)
- SECRET_KEY (64-character random string)
- JWT_SECRET_KEY (64-character random string)
- OLLAMA_URL (Ollama server URL)
- GITHUB_CLIENT_ID/SECRET (for OAuth)

## Post-Deployment Steps

1. **Setup Ollama Model**
   ```bash
   # SSH into your server or container
   ollama pull codellama:7b
   ```

2. **Initialize Database**
   ```bash
   # Run database migrations
   python -c "from backend.models import db; db.create_all()"
   ```

3. **Test Deployment**
   - Visit your domain
   - Test user registration
   - Create a game and test AI grading
   - Check logs for any errors

## Monitoring

- Check application logs: `docker logs cs-gauntlet`
- Monitor Ollama: `curl http://localhost:11434/api/tags`
- Check Redis: `redis-cli ping`
- Database health: Check connection in app logs

## Scaling

For high traffic:
1. Use multiple app instances behind load balancer
2. Use managed PostgreSQL (AWS RDS, etc.)
3. Use managed Redis (AWS ElastiCache, etc.)
4. Consider GPU instances for Ollama

## Security Checklist

- [ ] HTTPS enabled with valid SSL certificates
- [ ] Environment variables secured
- [ ] Database connections encrypted
- [ ] Regular security updates
- [ ] Monitoring and alerting configured
- [ ] Backup strategy implemented

## Troubleshooting

Common issues:
- Ollama not responding: Check if model is pulled
- Database connection: Verify DATABASE_URL
- Redis connection: Verify REDIS_URL
- WebSocket issues: Check proxy configuration
"""
    
    with open('DEPLOYMENT_GUIDE.md', 'w') as f:
        f.write(guide_content)
    
    print("✅ DEPLOYMENT_GUIDE.md created")
    return True

def main():
    """Main deployment preparation function"""
    print_banner()
    
    print("🎯 Preparing CS Gauntlet for production deployment...")
    print()
    
    # Generate all deployment files
    steps = [
        ("Generate production environment", generate_production_env),
        ("Create Dockerfile", create_dockerfile),
        ("Create docker-compose.yml", create_docker_compose),
        ("Create Nginx configuration", create_nginx_config),
        ("Create deployment guide", create_deployment_guide)
    ]
    
    for step_name, step_func in steps:
        print(f"📋 {step_name}...")
        if not step_func():
            print(f"❌ Failed: {step_name}")
            return 1
        print()
    
    print("🎉 Production deployment files created successfully!")
    print("=" * 60)
    print("📁 Files created:")
    print("   - production.env (update with your config)")
    print("   - Dockerfile")
    print("   - docker-compose.yml")
    print("   - nginx.conf (update domain and SSL)")
    print("   - DEPLOYMENT_GUIDE.md")
    print()
    print("🚀 Next steps:")
    print("1. Update production.env with your database and domain")
    print("2. Add SSL certificates to ./ssl/ directory")
    print("3. Choose deployment method from DEPLOYMENT_GUIDE.md")
    print("4. Deploy and test!")
    print()
    print("💡 For quick local production test:")
    print("   docker-compose up -d")
    print("=" * 60)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
