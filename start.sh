#!/bin/bash

# CS Gauntlet - Complete System Startup Script
# This script starts all required services for the CS Gauntlet platform

set -e

echo "🎮 Starting CS Gauntlet - Competitive Programming Platform"
echo "============================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a service is running
check_service() {
    local service=$1
    local port=$2
    if nc -z localhost $port 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $service is running on port $port"
        return 0
    else
        echo -e "${RED}✗${NC} $service is not running on port $port"
        return 1
    fi
}

# Check prerequisites
echo -e "${BLUE}📋 Checking prerequisites...${NC}"

if ! command_exists python3; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    exit 1
fi

if ! command_exists node; then
    echo -e "${RED}❌ Node.js is not installed${NC}"
    exit 1
fi

if ! command_exists redis-server; then
    echo -e "${YELLOW}⚠️  Redis is not installed - some features may not work${NC}"
fi

if ! command_exists docker; then
    echo -e "${YELLOW}⚠️  Docker is not installed - code execution will be limited${NC}"
fi

echo -e "${GREEN}✓${NC} Prerequisites check completed"

# Start Redis if not running
echo -e "\n${BLUE}🔴 Starting Redis...${NC}"
if ! check_service "Redis" 6379; then
    if command_exists redis-server; then
        echo "Starting Redis server..."
        redis-server --daemonize yes --port 6379
        sleep 2
        if check_service "Redis" 6379; then
            echo -e "${GREEN}✓${NC} Redis started successfully"
        else
            echo -e "${YELLOW}⚠️  Could not start Redis - continuing without it${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Redis not available - some features will be limited${NC}"
    fi
else
    echo -e "${GREEN}✓${NC} Redis is already running"
fi

# Check Docker
echo -e "\n${BLUE}🐳 Checking Docker...${NC}"
if command_exists docker; then
    if docker info >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Docker is running"
    else
        echo -e "${YELLOW}⚠️  Docker daemon is not running - please start Docker Desktop${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Docker not available - code execution will use fallback mode${NC}"
fi

# Check Ollama (optional)
echo -e "\n${BLUE}🤖 Checking Ollama (AI Grading)...${NC}"
if command_exists ollama; then
    if check_service "Ollama" 11434; then
        echo -e "${GREEN}✓${NC} Ollama is running - AI grading available"
    else
        echo -e "${YELLOW}⚠️  Ollama not running - starting it...${NC}"
        ollama serve &
        sleep 3
        if check_service "Ollama" 11434; then
            echo -e "${GREEN}✓${NC} Ollama started successfully"
            echo "Pulling CodeLlama model (this may take a while on first run)..."
            ollama pull codellama:7b
        else
            echo -e "${YELLOW}⚠️  Could not start Ollama - AI grading will use fallback${NC}"
        fi
    fi
else
    echo -e "${YELLOW}⚠️  Ollama not installed - AI grading will use fallback mode${NC}"
    echo "    To install: https://ollama.ai/"
fi

# Setup backend
echo -e "\n${BLUE}🐍 Setting up backend...${NC}"
cd backend

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Setup environment file
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Please edit backend/.env with your configuration${NC}"
fi

# Start backend
echo -e "\n${BLUE}🚀 Starting backend server...${NC}"
python app.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 5
if check_service "Backend" 5001; then
    echo -e "${GREEN}✓${NC} Backend started successfully (PID: $BACKEND_PID)"
else
    echo -e "${RED}❌ Backend failed to start${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

# Setup frontend
echo -e "\n${BLUE}⚛️  Setting up frontend...${NC}"
cd ../frontend

# Install dependencies
if [ ! -d "node_modules" ]; then
    echo "Installing Node.js dependencies..."
    npm install
fi

# Start frontend
echo -e "\n${BLUE}🌐 Starting frontend server...${NC}"
npm run dev &
FRONTEND_PID=$!

# Wait for frontend to start
sleep 5
if check_service "Frontend" 3000; then
    echo -e "${GREEN}✓${NC} Frontend started successfully (PID: $FRONTEND_PID)"
else
    echo -e "${RED}❌ Frontend failed to start${NC}"
    kill $FRONTEND_PID 2>/dev/null || true
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

# Success message
echo -e "\n${GREEN}🎉 CS Gauntlet is now running!${NC}"
echo "============================================================"
echo -e "🌐 Frontend:     ${BLUE}http://localhost:3000${NC}"
echo -e "🔧 Backend API:  ${BLUE}http://localhost:5001${NC}"
echo -e "📊 Health Check: ${BLUE}http://localhost:5001/health${NC}"
echo "============================================================"
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"

# Create cleanup function
cleanup() {
    echo -e "\n${YELLOW}🛑 Shutting down CS Gauntlet...${NC}"
    kill $FRONTEND_PID 2>/dev/null || true
    kill $BACKEND_PID 2>/dev/null || true
    echo -e "${GREEN}✓${NC} All services stopped"
    exit 0
}

# Set trap for cleanup
trap cleanup SIGINT SIGTERM

# Wait for processes
wait $FRONTEND_PID $BACKEND_PID
