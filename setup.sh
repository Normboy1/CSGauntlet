#!/bin/bash

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

# Create and activate Python virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Install frontend dependencies
echo "Installing frontend dependencies..."
cd frontend
npm install
cd ..

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p backend/static/uploads/profile_photos
mkdir -p backend/static/uploads/college_logos
mkdir -p backend/logs

# Create environment files
echo "Creating environment files..."

# Backend .env
cat > backend/.env << EOL
FLASK_APP=backend
FLASK_ENV=development
SECRET_KEY=$(openssl rand -hex 32)
DATABASE_URL=sqlite:///whos_quicker.db
CORS_ORIGINS=http://localhost:3000
SOCKET_URL=http://localhost:5001
OPENAI_API_KEY=your-openai-api-key-here
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
EOL

# Frontend .env
cat > frontend/.env << EOL
REACT_APP_SOCKET_URL=http://localhost:5001
REACT_APP_API_URL=http://localhost:5001
REACT_APP_ENV=development
EOL

echo "Setup complete! Please update the .env files with your actual API keys and credentials."
echo "To start the application:"
echo "1. Start the backend: cd backend && flask run"
echo "2. Start the frontend: cd frontend && npm start" 