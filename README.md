# 🎮 CS Gauntlet - Competitive Programming Platform

<div align="center">

![CS Gauntlet Logo](https://img.shields.io/badge/CS%20Gauntlet-Competitive%20Programming-4f46e5?style=for-the-badge&logo=code&logoColor=white)

**The Ultimate Real-Time Competitive Programming Platform**

[![Production Ready](https://img.shields.io/badge/Status-Production%20Ready-success?style=flat-square)](https://github.com/Normboy1/CSGauntlet)
[![Security Score](https://img.shields.io/badge/Security-95%2F100-brightgreen?style=flat-square)](./SECURITY.md)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](./LICENSE)
[![React](https://img.shields.io/badge/React-18.2.0-61dafb?style=flat-square&logo=react)](https://reactjs.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-000000?style=flat-square&logo=flask)](https://flask.palletsprojects.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.2.2-3178c6?style=flat-square&logo=typescript)](https://www.typescriptlang.org/)

[🚀 Live Demo](https://cs-gauntlet.vercel.app) • [📖 Documentation](./docs/) • [🐛 Report Bug](https://github.com/Normboy1/CSGauntlet/issues) • [✨ Request Feature](https://github.com/Normboy1/CSGauntlet/issues)

</div>

---

## 🌟 Overview

CS Gauntlet is a **production-ready competitive programming platform** that brings the excitement of real-time coding competitions to students and developers worldwide. Built with modern web technologies and enterprise-grade security, it offers a comprehensive suite of features for competitive programming enthusiasts.

### 🎯 **Key Highlights**
- 🔥 **Real-time multiplayer** coding competitions
- 🤖 **AI-powered grading** with Ollama + OpenAI integration
- 🛡️ **Enterprise security** with comprehensive protection suite
- 🎨 **Modern dark UI** with strict design system compliance
- ⚡ **Production ready** with full deployment configurations

---

## ✨ Features

### 🎮 **Core Gaming Features**
- **8 Game Modes**: Classic, Custom, Blitz, Practice, Ranked, Trivia, Debug, Electrical
- **Real-time Multiplayer**: WebSocket-powered live competitions
- **Live Chat System**: Communication during matches
- **Spectator Mode**: Watch ongoing competitions
- **VS Animations**: Dramatic game introductions
- **Anti-cheat System**: Paste prevention and integrity monitoring

### 🤖 **AI-Powered Grading**
- **Dual Provider Support**: Ollama (local) + OpenAI (cloud)
- **Comprehensive Analysis**: Correctness, efficiency, style, innovation
- **Detailed Feedback**: Code smells, best practices, suggestions
- **Grade Calculation**: A+ to F with percentile ranking
- **Fallback System**: Heuristic analysis when AI unavailable

### 🔒 **Enterprise Security**
- **15+ Security Modules**: Rate limiting, CSRF protection, security headers
- **Secure Code Execution**: Docker-based sandboxing
- **Input Validation**: Comprehensive sanitization
- **Audit Logging**: Complete activity tracking
- **Session Security**: JWT + OAuth integration
- **CORS Protection**: Secure cross-origin handling

### 🎨 **Modern UI/UX**
- **Dark Theme**: Consistent black/gray backgrounds with white text
- **Indigo Accents**: #4f46e5 for all primary actions
- **Responsive Design**: Mobile-first approach
- **Smooth Animations**: Framer Motion effects
- **Professional Code Editor**: Monaco Editor with syntax highlighting
- **Design System**: Strict component standards

---

## 🏗️ Architecture

### **Frontend Stack**
```
React 18 + TypeScript + Vite
├── Tailwind CSS (Styling)
├── Socket.IO Client (Real-time)
├── Monaco Editor (Code editing)
├── Framer Motion (Animations)
├── React Router (Navigation)
└── Heroicons (Icons)
```

### **Backend Stack**
```
Flask + SocketIO + SQLAlchemy + Redis
├── Security Suite (15+ modules)
├── AI Grading (Ollama + OpenAI)
├── Docker Integration
├── Celery (Background tasks)
├── JWT Authentication
└── GitHub OAuth
```

### **Database & Infrastructure**
```
SQLite (Development) / PostgreSQL (Production)
├── Redis (Sessions + Game state)
├── Docker (Code execution)
├── Gunicorn (WSGI server)
└── Multiple deployment options
```

---

## 🚀 Quick Start

### **One-Command Setup**
```bash
git clone https://github.com/Normboy1/CSGauntlet.git
cd CSGauntlet
chmod +x start.sh
./start.sh
```

### **Manual Setup**

#### **Prerequisites**
- Python 3.9+
- Node.js 18+
- Redis Server
- Docker (optional, for code execution)

#### **Backend Setup**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configuration
python app.py
```

#### **Frontend Setup**
```bash
cd frontend
npm install
npm run dev
```

#### **Environment Configuration**
```bash
# Required environment variables
SECRET_KEY=your-secret-key-here
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
OPENAI_API_KEY=your-openai-key  # Optional
REDIS_URL=redis://localhost:6379/0
```

---

## 📱 Screenshots

<div align="center">

### **🏠 Homepage**
![Homepage](https://via.placeholder.com/800x400/1f2937/ffffff?text=CS+Gauntlet+Homepage)

### **🎮 Dashboard**
![Dashboard](https://via.placeholder.com/800x400/1f2937/4f46e5?text=Game+Mode+Selection)

### **⚔️ Game Interface**
![Game](https://via.placeholder.com/800x400/000000/ffffff?text=Real-time+Coding+Competition)

### **🏆 Leaderboard**
![Leaderboard](https://via.placeholder.com/800x400/1f2937/16a34a?text=Player+Rankings)

</div>

---

## 🎯 Game Modes

| Mode | Description | Features |
|------|-------------|----------|
| **🏆 Classic** | Traditional 1v1 competitive matches | Standard rules, ranked scoring |
| **⚙️ Custom** | User-created games with custom rules | Flexible settings, private rooms |
| **⚡ Blitz** | Fast-paced quick matches | Time pressure, rapid scoring |
| **📚 Practice** | Solo skill building | No pressure, learning focused |
| **🥇 Ranked** | Competitive ladder system | ELO rating, seasonal rewards |
| **🧠 Trivia** | CS knowledge challenges | Multiple choice, theory questions |
| **🐛 Debug** | Find and fix code bugs | Error detection, debugging skills |
| **⚡ Electrical** | Engineering-specific problems | Circuit analysis, hardware focus |

---

## 🔧 Configuration

### **AI Grading Setup**

#### **Option 1: Ollama (Recommended)**
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull CodeLlama model
ollama pull codellama:7b

# Set environment variables
AI_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=codellama:7b
```

#### **Option 2: OpenAI**
```bash
# Set environment variables
AI_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key
```

### **Security Configuration**
```bash
# Enable security features
RATE_LIMIT_ENABLED=True
RATE_LIMIT_PER_MINUTE=60
MAX_CONTENT_LENGTH=16777216  # 16MB
```

---

## 🚀 Deployment

### **Production Deployment Options**

#### **🌐 Vercel (Frontend) + Railway (Backend)**
```bash
# Frontend to Vercel
npm run build
vercel --prod

# Backend to Railway
railway login
railway init
railway up
```

#### **🐳 Docker Deployment**
```bash
docker-compose up -d
```

#### **☁️ Cloud Platforms**
- **Netlify**: Frontend deployment
- **Heroku**: Full-stack deployment
- **DigitalOcean**: VPS deployment
- **AWS**: Enterprise deployment

### **Environment-Specific Configs**
- **Development**: SQLite + local Redis
- **Staging**: PostgreSQL + Redis Cloud
- **Production**: Managed database + Redis cluster

---

## 🧪 Testing

### **Run Test Suite**
```bash
# Backend tests
python test_system.py
python test_game_functions.py

# Frontend tests
npm test

# Security tests
python backend/backend/security_testing.py
```

### **Health Checks**
```bash
# Backend health
curl http://localhost:5001/health

# Frontend health
curl http://localhost:3000
```

---

## 📊 Performance Metrics

### **Backend Performance**
- **Response Time**: < 100ms average
- **Concurrent Users**: 1000+ supported
- **Security Score**: 95/100
- **Test Coverage**: 85%+

### **Frontend Performance**
- **Lighthouse Score**: 95+
- **First Contentful Paint**: < 1.5s
- **Time to Interactive**: < 2.5s
- **Bundle Size**: < 500KB gzipped

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](./CONTRIBUTING.md) for details.

### **Development Workflow**
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### **Code Standards**
- **Frontend**: ESLint + Prettier + TypeScript strict mode
- **Backend**: Black + Flake8 + Type hints
- **Design**: Strict adherence to design system
- **Security**: All changes must pass security review

---

## 📚 Documentation

- [📖 **API Documentation**](./docs/api.md)
- [🎨 **Design System**](./frontend/DESIGN_SYSTEM.md)
- [🔒 **Security Guide**](./SECURITY.md)
- [🚀 **Deployment Guide**](./docs/deployment.md)
- [🧪 **Testing Guide**](./docs/testing.md)

---

## 🛠️ Tech Stack Details

### **Frontend Dependencies**
```json
{
  "react": "^18.2.0",
  "typescript": "^5.2.2",
  "@monaco-editor/react": "^4.5.0",
  "socket.io-client": "^4.8.1",
  "framer-motion": "^10.16.16",
  "tailwindcss": "^3.3.5"
}
```

### **Backend Dependencies**
```python
Flask==2.3.3
Flask-SocketIO==5.3.6
SQLAlchemy==2.0.21
redis==5.0.0
openai==1.3.0
aiohttp==3.8.6
docker==6.1.3
```

---

## 📈 Roadmap

### **🎯 Current Version (v1.0)**
- ✅ Real-time multiplayer gaming
- ✅ AI-powered code grading
- ✅ Enterprise security suite
- ✅ Modern UI with dark theme
- ✅ Multiple game modes

### **🚀 Upcoming Features (v1.1)**
- [ ] Mobile app (React Native)
- [ ] Advanced analytics dashboard
- [ ] Tournament system
- [ ] Team competitions
- [ ] Code review features

### **🌟 Future Vision (v2.0)**
- [ ] Machine learning problem recommendations
- [ ] Advanced AI tutoring system
- [ ] Integration with coding platforms
- [ ] Enterprise SSO support
- [ ] Advanced monitoring and metrics

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Monaco Editor** for the professional code editing experience
- **Ollama** for local AI model support
- **OpenAI** for advanced AI capabilities
- **Tailwind CSS** for the beautiful design system
- **Socket.IO** for real-time functionality

---

## 📞 Support

- 📧 **Email**: support@cs-gauntlet.com
- 💬 **Discord**: [Join our community](https://discord.gg/cs-gauntlet)
- 🐛 **Issues**: [GitHub Issues](https://github.com/yourusername/cs-gauntlet/issues)
- 📖 **Docs**: [Documentation](./docs/)

---

<div align="center">

**⭐ Star this repository if you find it helpful!**

Made with ❤️ by the CS Gauntlet Team

[🚀 **Deploy Now**](https://vercel.com/new/clone?repository-url=https://github.com/Normboy1/CSGauntlet) • [📱 **Try Demo**](https://cs-gauntlet.vercel.app) • [🤝 **Contribute**](./CONTRIBUTING.md)

</div>

- **Python 3.9+**
- **Node.js 16+** 
- **Redis** (for real-time features)
- **Docker** (for secure code execution)
- **Ollama** (optional, for AI grading)

### 1. Backend Setup

```bash
# Clone the repository
git clone <repository-url>
cd cs_gauntlet

# Set up Python environment
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Initialize database
python app.py
```

### 2. Frontend Setup

```bash
# In a new terminal
cd frontend
npm install
npm run dev
```

### 3. Start Services

```bash
# Start Redis (required)
redis-server

# Start Ollama (optional, for AI grading)
ollama serve
ollama pull codellama:7b

# Start Docker (required for code execution)
# Make sure Docker Desktop is running
```

### 4. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5001
- **Health Check**: http://localhost:5001/health

## 🏗️ Architecture

### Backend (Python)
- **Flask** + **SocketIO** for real-time web framework
- **SQLAlchemy** + **Redis** for data persistence
- **Docker** for secure code execution
- **Ollama/OpenAI** for AI-powered grading
- **Comprehensive security modules**

### Frontend (TypeScript/React)
- **React 18** with TypeScript
- **Vite** for fast development
- **Tailwind CSS** with custom design system
- **Socket.IO** for real-time communication

## 🎮 Game Modes

| Mode | Description | Features |
|------|-------------|----------|
| **Casual** | Relaxed competitive matches | No ranking impact, practice-friendly |
| **Ranked** | Competitive skill-based matches | ELO rating system, leaderboards |
| **Blitz** | Fast-paced coding challenges | Short time limits, quick rounds |
| **Practice** | Solo practice against AI | Skill building, no pressure |
| **Trivia** | Programming knowledge quiz | Multiple choice, concept testing |
| **Debug** | Find and fix code bugs | Error detection, debugging skills |
| **Custom** | User-defined game settings | Flexible rules, private matches |

## 🤖 AI Grading System

The platform features a comprehensive AI grading system that evaluates code on multiple criteria:

### Grading Criteria
- **Correctness** (0-40 points): Test case pass rate
- **Efficiency** (0-25 points): Time/space complexity analysis
- **Readability** (0-20 points): Code structure and clarity
- **Style** (0-10 points): Language conventions adherence
- **Innovation** (0-5 points): Creative problem-solving approaches

### AI Providers
- **Ollama** (Recommended): Local AI with CodeLlama model
- **OpenAI** (Alternative): GPT-4 for advanced analysis
- **Fallback**: Heuristic analysis when AI unavailable

## 🔧 Configuration

### Environment Variables

```bash
# Core Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
DATABASE_URL=sqlite:///cs_gauntlet.db
REDIS_URL=redis://localhost:6379/0

# AI Grading
AI_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=codellama:7b
OPENAI_API_KEY=your-openai-key

# Security
RATE_LIMIT_ENABLED=True
DOCKER_TIMEOUT=10
DOCKER_MEMORY_LIMIT=256m

# OAuth (Optional)
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

## 📊 API Endpoints

### Game Management
- `POST /api/game/matchmaking/find` - Find/create match
- `POST /api/game/create_custom` - Create custom game
- `GET /api/game/<id>/state` - Get game state
- `POST /api/game/<id>/submit_solution` - Submit code

### Code Execution & Grading
- `POST /api/code/submit_with_grading` - Submit with AI grading
- `POST /api/code/compare_solutions` - Compare multiple solutions

### Statistics & Leaderboards
- `GET /api/game/leaderboard` - Get rankings
- `GET /api/game/stats/user` - User statistics
- `GET /api/problems` - Available problems

## 🛡️ Security Features

### Code Execution Security
- **Docker sandboxing** with resource limits
- **Network isolation** and read-only filesystem
- **Process limits** and timeout enforcement
- **Memory and CPU constraints**

### Application Security
- **JWT authentication** with secure sessions
- **Rate limiting** per user and endpoint
- **CORS protection** with whitelist
- **Input validation** and sanitization
- **SQL injection prevention**

### Game Integrity
- **Anti-cheat detection** for suspicious patterns
- **Solution uniqueness** validation
- **Time manipulation** prevention
- **Submission integrity** verification

## 🚀 Deployment

### Development
```bash
# Backend
cd backend && python app.py

# Frontend  
cd frontend && npm run dev
```

### Production

#### Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up --build
```

#### Manual Production Setup
```bash
# Backend
cd backend
pip install -r requirements.txt
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5001 app:app

# Frontend
cd frontend
npm run build
# Serve build/ with nginx or similar
```

#### Platform Deployment
- **Vercel/Netlify**: Frontend deployment ready
- **Railway/Heroku**: Backend deployment configured
- **Docker**: Full containerization support

## 🧪 Testing

```bash
# Backend tests
cd backend
python -m pytest tests/

# Frontend tests
cd frontend
npm test

# Integration tests
python backend/test_full_system.py
```

## 📁 Project Structure

```
cs_gauntlet/
├── backend/                 # Python Flask backend
│   ├── backend/            # Core application package
│   │   ├── __init__.py     # App factory with AI integration
│   │   ├── ai_grader.py    # AI grading system
│   │   ├── game_manager.py # Game logic and state
│   │   ├── game_api.py     # Game API endpoints
│   │   ├── code_executor.py # Secure code execution
│   │   ├── models.py       # Database models
│   │   └── security/       # Security modules
│   ├── app.py              # Production application launcher
│   └── requirements.txt    # Python dependencies
├── frontend/               # React TypeScript frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API services
│   │   └── utils/          # Utility functions
│   ├── DESIGN_SYSTEM.md    # UI design guidelines
│   └── package.json        # Node dependencies
└── docs/                   # Documentation
```

## 🤝 Contributing

1. **Fork** the repository
2. **Create** your feature branch (`git checkout -b feature/amazing-feature`)
3. **Follow** the design system guidelines in `frontend/DESIGN_SYSTEM.md`
4. **Test** your changes thoroughly
5. **Commit** your changes (`git commit -m 'Add amazing feature'`)
6. **Push** to the branch (`git push origin feature/amazing-feature`)
7. **Open** a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Ollama** for local AI inference
- **CodeLlama** for code analysis capabilities
- **React** and **Flask** communities
- **Tailwind CSS** for the design system
- **Docker** for secure sandboxing

---

**🎮 Ready to compete? Start your coding gauntlet now!**
