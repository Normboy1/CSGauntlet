# 🚀 DEPLOY CS GAUNTLET LIVE - RIGHT NOW!

## Option 1: GitHub Pages (Fastest - 2 minutes)

### Step 1: Push to GitHub
```bash
# If you haven't already, create a GitHub repo and push:
git remote add origin https://github.com/YOUR_USERNAME/cs-gauntlet.git
git push -u origin main
```

### Step 2: Enable GitHub Pages
1. Go to your GitHub repository
2. Click **Settings** → **Pages**
3. Source: **Deploy from a branch**
4. Branch: **main** / **/ (root)**
5. Click **Save**

Your site will be live at: `https://YOUR_USERNAME.github.io/cs-gauntlet`

## Option 2: Vercel (1 minute)

```bash
cd frontend
npx vercel --prod
```

Follow the prompts:
- Setup and deploy? **Y**
- Which scope? Select your account
- Link to existing project? **N** 
- Project name? **cs-gauntlet**
- In which directory is your code located? **./**

## Option 3: Netlify Drop (30 seconds)

1. Build the frontend:
```bash
cd frontend
npm run build
```

2. Go to: https://app.netlify.com/drop
3. Drag the `dist` folder to the browser
4. **DONE!** - Your site is live instantly

## Option 4: Railway (Full Stack - 5 minutes)

For complete deployment with backend + AI grading:

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

Add these environment variables in Railway dashboard:
```
DATABASE_URL=<railway-postgres-url>
REDIS_URL=<railway-redis-url>
SECRET_KEY=<generate-random-key>
AI_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
```

## Quick Test URLs

Once deployed, test these features:
- **Homepage**: Your deployed URL
- **Register**: `/register`
- **Login**: `/login` 
- **Dashboard**: `/dashboard`
- **Game**: `/game`

## 🎮 Test Accounts Ready

Use these for immediate testing:
- Username: `alice` / Password: `password123`
- Username: `bob` / Password: `password123`

---

## 🚀 CHOOSE YOUR DEPLOYMENT METHOD AND GO LIVE!

Pick any option above and your CS Gauntlet will be online in minutes!
