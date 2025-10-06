# 🚀 DEPLOY CS GAUNTLET ONLINE - QUICK GUIDE

## Option 1: Deploy to Vercel (Easiest - 2 minutes)

### Step 1: Build the frontend
```bash
cd frontend
npm install
npm run build
```

### Step 2: Deploy to Vercel
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy (from frontend directory)
vercel

# Follow the prompts:
# - Setup and deploy? Y
# - Which scope? (select your account)
# - Link to existing project? N
# - Project name? cs-gauntlet-arena
# - In which directory is your code located? ./
# - Want to modify settings? N
```

Your app will be live at: https://cs-gauntlet-arena.vercel.app

## Option 2: Deploy to Netlify (Alternative - 3 minutes)

### Step 1: Build the frontend
```bash
cd frontend
npm install
npm run build
```

### Step 2: Deploy to Netlify
```bash
# Install Netlify CLI
npm i -g netlify-cli

# Deploy (from frontend directory)
netlify deploy --prod --dir=dist

# Or use drag & drop:
# 1. Go to https://app.netlify.com/drop
# 2. Drag the 'dist' folder to the browser
```

## Option 3: Deploy Full Stack to Railway (Complete solution - 5 minutes)

### Step 1: Create a Railway account
Go to https://railway.app and sign up

### Step 2: Deploy via GitHub
1. Push your code to GitHub
2. In Railway, click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository
5. Railway will auto-detect and deploy both frontend and backend

### Step 3: Add services
In Railway dashboard:
- Add PostgreSQL database
- Add Redis instance
- Set environment variables from .env.example

## Option 4: Deploy to Render (Free tier available)

### Frontend on Render
1. Go to https://render.com
2. New > Static Site
3. Connect your GitHub repo
4. Build Command: `cd frontend && npm install && npm run build`
5. Publish Directory: `frontend/dist`

### Backend on Render
1. New > Web Service
2. Connect same repo
3. Build Command: `pip install -r backend/requirements.txt`
4. Start Command: `cd backend && python run_enhanced.py`

## Environment Variables for Production

Add these to your deployment platform:

```env
# Backend (if deploying backend)
SECRET_KEY=generate-a-secure-random-key
DATABASE_URL=your-postgres-url
REDIS_URL=your-redis-url
AI_PROVIDER=ollama
OLLAMA_URL=http://your-ollama-server:11434
OLLAMA_MODEL=codellama:7b

# Frontend (update API endpoint)
VITE_API_URL=https://your-backend-url.com
```

## Quick Local Test Before Deploy

```bash
# Terminal 1 - Backend
cd backend
python run_enhanced.py

# Terminal 2 - Frontend
cd frontend
npm run dev

# Terminal 3 - Ollama (for AI grading)
ollama serve
ollama pull codellama:7b
```

Visit http://localhost:5173

## 🎯 FASTEST OPTION: Static Deploy (Frontend Only)

If you just want to get the frontend online NOW:

```bash
cd frontend
npm install
npm run build
npx surge dist cs-gauntlet.surge.sh
```

Your site will be live in 30 seconds at: http://cs-gauntlet.surge.sh

---

## Backend Deployment (Optional - for full functionality)

The backend with Ollama AI grading needs a server. Options:

1. **Heroku** (Easy but paid)
2. **Railway** (Recommended - has free tier)
3. **DigitalOcean App Platform**
4. **AWS EC2** (Most control)
5. **Google Cloud Run**

For Railway (recommended):
```bash
railway login
railway init
railway up
```

---

## 🎉 That's it! Your CS Gauntlet is going live!

Choose any option above and your competitive programming platform with AI grading will be online in minutes!
