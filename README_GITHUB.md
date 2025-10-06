# 🎮 CS Gauntlet - Competitive Programming Platform with AI Grading

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.9+-blue)
![React](https://img.shields.io/badge/react-18.0+-61dafb)
![Security](https://img.shields.io/badge/security-95%2F100-success)

A real-time competitive programming platform featuring AI-powered code grading using Ollama, multiplayer battles, and comprehensive game modes.

## ✨ Features

### 🤖 AI-Powered Grading
- **Ollama Integration**: Uses CodeLlama for intelligent code analysis
- **Multi-criteria Evaluation**: Correctness, efficiency, readability, style, innovation
- **Instant Feedback**: Detailed suggestions for improvement

### 🎮 Game Modes
- **Casual Mode**: Relaxed competitive programming
- **Ranked Mode**: ELO-based matchmaking system
- **Trivia Mode**: Computer science trivia challenges
- **Debug Mode**: Fix broken code challenges

### 🔐 Security
- Enterprise-grade security (95/100 score)
- OAuth integration (GitHub)
- Rate limiting and anti-cheating measures
- Secure session management

### 💻 Technology Stack

**Backend:**
- Flask + Flask-SocketIO
- SQLAlchemy + PostgreSQL
- Redis for sessions/caching
- Celery for background tasks
- Ollama for AI grading

**Frontend:**
- React 18 + TypeScript
- Vite + Tailwind CSS
- Socket.IO Client
- Framer Motion animations

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- Redis
- Ollama (for AI grading)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/cs-gauntlet.git
cd cs-gauntlet
```

2. **Setup Backend**
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configuration
```

3. **Setup Frontend**
```bash
cd frontend
npm install
```

4. **Setup Ollama (for AI grading)**
```bash
# Install Ollama from https://ollama.ai
ollama serve
ollama pull codellama:7b
```

5. **Run Development Servers**
```bash
# Terminal 1 - Backend
cd backend
python run_enhanced.py

# Terminal 2 - Frontend
cd frontend
npm run dev
```

Visit http://localhost:5173 to see the application!

## 🎯 Test Accounts

For quick testing, use these pre-configured accounts:
- `alice` / `password123`
- `bob` / `password123`
- `charlie` / `password123`

## 🌐 Deployment

### Deploy to Vercel (Frontend)
```bash
cd frontend
npx vercel
```

### Deploy to Railway (Full Stack)
```bash
railway init
railway up
```

### Docker Deployment
```bash
docker-compose up -d
```

## 📸 Screenshots

### Game Interface
- Real-time multiplayer battles
- Live code editor with syntax highlighting
- AI grading results with detailed feedback

### Features
- ✅ Real-time WebSocket communication
- ✅ AI-powered code analysis
- ✅ Comprehensive game modes
- ✅ Spectator system
- ✅ In-game chat
- ✅ Leaderboards

## 🔧 Configuration

### Environment Variables
```env
# Backend
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://...
REDIS_URL=redis://localhost:6379

# AI Grading
AI_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=codellama:7b

# OAuth (optional)
GITHUB_CLIENT_ID=your-client-id
GITHUB_CLIENT_SECRET=your-client-secret
```

## 📚 Documentation

### 🎯 Quick Start
- [Launch Checklist](LAUNCH_CHECKLIST.md) - Week of launch guide
- [Deployment Guide](DEPLOY_NOW.md) - Multiple deployment options
- [Git Setup](git_commands.md) - GitHub setup instructions

### 🎮 Game & Features
- [Game Functionality Status](GAME_FUNCTIONALITY_STATUS.md) - Complete feature overview
- [Verified Working](VERIFIED_WORKING.md) - All systems verification
- [Launch Guide](LAUNCH_GUIDE.md) - Production readiness guide

### 🎨 Design & Styling
- [Design System](frontend/DESIGN_SYSTEM.md) - Complete design system with color palette
- [Styling Guide](frontend/STYLING_GUIDE.md) - Component styling rules and standards
- [Styling README](frontend/STYLING_README.md) - Quick styling reference

### 🔒 Security
- [Security Status](SECURITY_STATUS.md) - Security implementation (95/100 score)
- [Security Overview](SECURITY.md) - Security measures and protocols

### 🏗️ Architecture
- [Project Structure](PROJECT_STRUCTURE.md) - Complete file organization
- [Documentation Index](docs/README.md) - All documentation overview

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Ollama for providing local AI capabilities
- The open-source community for amazing tools and libraries

---

**Built with ❤️ for competitive programmers**

⭐ Star this repo if you find it useful!
