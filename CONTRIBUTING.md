# 🤝 Contributing to CS Gauntlet

Thank you for your interest in contributing to CS Gauntlet! We welcome contributions from developers of all skill levels.

## 🚀 Quick Start for Contributors

### 1. Fork & Clone
```bash
git clone https://github.com/yourusername/cs-gauntlet.git
cd cs-gauntlet
```

### 2. Set Up Development Environment
```bash
# Backend setup
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Frontend setup
cd ../frontend
npm install
```

### 3. Run Development Servers
```bash
# Terminal 1: Backend
cd backend && python app.py

# Terminal 2: Frontend
cd frontend && npm run dev
```

## 📋 Development Guidelines

### **Code Standards**

#### **Frontend (React + TypeScript)**
- Use TypeScript strict mode
- Follow the design system strictly (dark theme + indigo accents)
- Use ESLint + Prettier for formatting
- Write meaningful component names
- Add proper TypeScript types

#### **Backend (Python + Flask)**
- Follow PEP 8 style guidelines
- Use type hints for all functions
- Write docstrings for all modules and functions
- Use Black for code formatting
- Add proper error handling

#### **Design System Compliance**
- **NEVER** change the dark theme
- **ALWAYS** use indigo (#4f46e5) for primary actions
- **MAINTAIN** consistent spacing and typography
- **FOLLOW** the component standards in `frontend/DESIGN_SYSTEM.md`

### **Git Workflow**

1. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Your Changes**
   - Write clean, documented code
   - Follow the coding standards
   - Add tests for new features

3. **Test Your Changes**
   ```bash
   # Backend tests
   python test_system.py
   
   # Frontend tests
   npm test
   
   # Security tests
   python backend/backend/security_testing.py
   ```

4. **Commit with Conventional Commits**
   ```bash
   git commit -m "feat: add new game mode"
   git commit -m "fix: resolve authentication bug"
   git commit -m "docs: update API documentation"
   ```

5. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

## 🎯 Areas for Contribution

### **🔥 High Priority**
- [ ] Mobile responsiveness improvements
- [ ] Performance optimizations
- [ ] Additional game modes
- [ ] Enhanced AI grading features
- [ ] Accessibility improvements

### **🚀 New Features**
- [ ] Tournament system
- [ ] Team competitions
- [ ] Advanced analytics
- [ ] Code review features
- [ ] Mobile app (React Native)

### **🐛 Bug Fixes**
- [ ] Cross-browser compatibility
- [ ] Edge case handling
- [ ] Performance bottlenecks
- [ ] UI/UX improvements

### **📚 Documentation**
- [ ] API documentation
- [ ] Deployment guides
- [ ] Tutorial content
- [ ] Code examples

## 🧪 Testing Requirements

### **Before Submitting a PR**
1. **All tests must pass**
   ```bash
   python test_system.py
   npm test
   ```

2. **Security tests must pass**
   ```bash
   python backend/backend/security_testing.py
   ```

3. **Code must follow style guidelines**
   ```bash
   # Backend
   black backend/
   flake8 backend/
   
   # Frontend
   npm run lint
   npm run format
   ```

4. **Design system compliance**
   - Verify dark theme is maintained
   - Check indigo accent usage
   - Test responsive design

## 📝 Pull Request Process

### **PR Template**
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Security tests pass
- [ ] Manual testing completed

## Design System
- [ ] Dark theme maintained
- [ ] Indigo accents used correctly
- [ ] Responsive design verified

## Screenshots (if applicable)
Add screenshots of UI changes
```

### **Review Process**
1. **Automated Checks**: All CI/CD checks must pass
2. **Code Review**: At least one maintainer review required
3. **Security Review**: Security-related changes need security team approval
4. **Design Review**: UI changes need design system compliance check

## 🏗️ Architecture Guidelines

### **Frontend Structure**
```
src/
├── components/     # Reusable UI components
├── pages/         # Route components
├── context/       # React context providers
├── utils/         # Utility functions
├── services/      # API services
└── constants/     # App constants
```

### **Backend Structure**
```
backend/
├── backend/       # Main application code
├── models.py      # Database models
├── auth.py        # Authentication logic
├── game_api.py    # Game-related endpoints
└── security/      # Security modules
```

## 🔒 Security Considerations

### **Security Requirements**
- All user inputs must be validated and sanitized
- Authentication must be properly implemented
- Rate limiting must be applied to all endpoints
- CORS must be properly configured
- All security tests must pass

### **Reporting Security Issues**
- **DO NOT** create public issues for security vulnerabilities
- Email security@cs-gauntlet.com with details
- We will respond within 24 hours
- Follow responsible disclosure practices

## 🎨 Design System Guidelines

### **Color Palette (NEVER CHANGE)**
- Primary Background: `bg-black` (#000000)
- Component Background: `bg-gray-800` (#1f2937)
- Primary Accent: `bg-indigo-600` (#4f46e5)
- Text: `text-white` (#ffffff)

### **Component Standards**
```tsx
// Button example
<button className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors">
  Click Me
</button>

// Card example
<div className="bg-gray-800 p-6 rounded-lg shadow-lg">
  Content here
</div>
```

## 📞 Getting Help

### **Communication Channels**
- **Discord**: [Join our community](https://discord.gg/cs-gauntlet)
- **GitHub Discussions**: For feature discussions
- **GitHub Issues**: For bug reports
- **Email**: dev@cs-gauntlet.com

### **Development Support**
- Check existing issues before creating new ones
- Use descriptive titles and detailed descriptions
- Include steps to reproduce for bugs
- Add screenshots for UI issues

## 🏆 Recognition

### **Contributors**
All contributors will be:
- Added to the contributors list
- Mentioned in release notes
- Invited to the contributors Discord channel
- Eligible for contributor swag

### **Maintainer Path**
Active contributors may be invited to become maintainers based on:
- Quality of contributions
- Community involvement
- Technical expertise
- Commitment to the project

## 📋 Code of Conduct

### **Our Standards**
- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Respect different viewpoints and experiences

### **Unacceptable Behavior**
- Harassment or discrimination
- Trolling or insulting comments
- Publishing private information
- Any conduct that would be inappropriate in a professional setting

## 🎉 Thank You!

Your contributions make CS Gauntlet better for everyone. Whether you're fixing bugs, adding features, improving documentation, or helping other contributors, your efforts are appreciated!

---

**Happy Coding! 🚀**
