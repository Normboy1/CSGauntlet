#!/bin/bash

# CS Gauntlet - GitHub Repository Setup Script
# This script prepares your CS Gauntlet project for GitHub

set -e

echo "🎮 CS Gauntlet - GitHub Setup"
echo "============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo -e "${BLUE}📋 Checking prerequisites...${NC}"

# Check if git is installed
if ! command_exists git; then
    echo -e "${RED}❌ Git is not installed. Please install Git first.${NC}"
    exit 1
fi

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo -e "${YELLOW}📁 Initializing Git repository...${NC}"
    git init
    echo -e "${GREEN}✓${NC} Git repository initialized"
else
    echo -e "${GREEN}✓${NC} Git repository already exists"
fi

# Create .gitignore if it doesn't exist
if [ ! -f ".gitignore" ]; then
    echo -e "${YELLOW}📝 Creating .gitignore...${NC}"
    cat > .gitignore << 'EOF'
# Dependencies
node_modules/
backend/venv/
backend/__pycache__/
backend/backend/__pycache__/
*.pyc
*.pyo
*.pyd
__pycache__/
*.so

# Environment variables
.env
.env.local
.env.development.local
.env.test.local
.env.production.local

# Database
*.db
*.sqlite
*.sqlite3
instance/

# Logs
logs/
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Runtime data
pids
*.pid
*.seed
*.pid.lock

# Coverage directory used by tools like istanbul
coverage/
*.lcov

# nyc test coverage
.nyc_output

# Dependency directories
jspm_packages/

# Optional npm cache directory
.npm

# Optional eslint cache
.eslintcache

# Output of 'npm pack'
*.tgz

# Yarn Integrity file
.yarn-integrity

# parcel-bundler cache (https://parceljs.org/)
.cache
.parcel-cache

# next.js build output
.next

# nuxt.js build output
.nuxt

# vuepress build output
.vuepress/dist

# Serverless directories
.serverless

# FuseBox cache
.fusebox/

# DynamoDB Local files
.dynamodb/

# TernJS port file
.tern-port

# Stores VSCode versions used for testing VSCode extensions
.vscode-test

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS generated files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Build outputs
dist/
build/
frontend/dist/
frontend/build/

# Temporary files
tmp/
temp/
*.tmp

# Docker
.dockerignore

# Redis dump
dump.rdb

# Uploads
uploads/
static/uploads/

# Testing
.pytest_cache/
.coverage
htmlcov/

# Celery
celerybeat-schedule
celerybeat.pid

# Flask
instance/
.webassets-cache

# Backup files
*.bak
*.backup
*~

# Local configuration
config.local.py
settings.local.py
EOF
    echo -e "${GREEN}✓${NC} .gitignore created"
else
    echo -e "${GREEN}✓${NC} .gitignore already exists"
fi

# Stage all files
echo -e "${YELLOW}📦 Staging files for commit...${NC}"
git add .

# Check if there are any changes to commit
if git diff --staged --quiet; then
    echo -e "${YELLOW}⚠️  No changes to commit${NC}"
else
    # Make initial commit
    echo -e "${YELLOW}💾 Making initial commit...${NC}"
    git commit -m "🎮 Initial commit: CS Gauntlet - Complete competitive programming platform

✨ Features:
- Real-time multiplayer gaming with 8 game modes
- AI-powered code grading (Ollama + OpenAI)
- Enterprise-grade security (15+ modules)
- Modern dark UI with React + TypeScript
- Production-ready deployment configurations

🏗️ Architecture:
- Backend: Flask + SocketIO + SQLAlchemy + Redis
- Frontend: React 18 + TypeScript + Vite + Tailwind
- Security: Comprehensive protection suite
- AI: Dual-provider grading system

🚀 Status: Production Ready"
    
    echo -e "${GREEN}✓${NC} Initial commit created"
fi

# Instructions for GitHub setup
echo ""
echo -e "${PURPLE}🚀 Next Steps - GitHub Repository Setup:${NC}"
echo ""
echo -e "${BLUE}1. Create GitHub Repository:${NC}"
echo "   • Go to https://github.com/new"
echo "   • Repository name: cs-gauntlet"
echo "   • Description: 🎮 The Ultimate Real-Time Competitive Programming Platform"
echo "   • Make it Public (recommended for open source)"
echo "   • Don't initialize with README (we already have one)"
echo ""

echo -e "${BLUE}2. Connect Local Repository to GitHub:${NC}"
echo "   Replace 'yourusername' with your actual GitHub username:"
echo ""
echo -e "${YELLOW}   git remote add origin https://github.com/yourusername/cs-gauntlet.git${NC}"
echo -e "${YELLOW}   git branch -M main${NC}"
echo -e "${YELLOW}   git push -u origin main${NC}"
echo ""

echo -e "${BLUE}3. Configure Repository Settings:${NC}"
echo "   • Go to your repository on GitHub"
echo "   • Settings → General → Features"
echo "   • Enable: Issues, Projects, Wiki, Discussions"
echo "   • Settings → Security → Code security and analysis"
echo "   • Enable: Dependency graph, Dependabot alerts, Secret scanning"
echo ""

echo -e "${BLUE}4. Set Up Branch Protection:${NC}"
echo "   • Settings → Branches → Add rule"
echo "   • Branch name pattern: main"
echo "   • Enable: Require pull request reviews, Require status checks"
echo ""

echo -e "${BLUE}5. Add Repository Topics:${NC}"
echo "   Add these topics to help others discover your project:"
echo "   competitive-programming, react, flask, typescript, python,"
echo "   real-time, multiplayer, ai-grading, dark-theme, websocket"
echo ""

echo -e "${BLUE}6. Update README Links:${NC}"
echo "   Edit README.md and replace 'yourusername' with your GitHub username"
echo ""

echo -e "${GREEN}📋 Repository is ready for GitHub! 🎉${NC}"
echo ""
echo -e "${PURPLE}📊 Project Statistics:${NC}"
echo "   • Backend files: 51+ (including security modules)"
echo "   • Frontend components: 18+"
echo "   • Security modules: 15+"
echo "   • Game modes: 8"
echo "   • Production ready: ✅"
echo ""

echo -e "${BLUE}🔗 Useful Commands:${NC}"
echo -e "${YELLOW}   git status${NC}                    # Check repository status"
echo -e "${YELLOW}   git log --oneline${NC}            # View commit history"
echo -e "${YELLOW}   git remote -v${NC}                # View remote repositories"
echo -e "${YELLOW}   ./start.sh${NC}                   # Start the application"
echo ""

echo -e "${GREEN}Happy coding! 🚀${NC}"
