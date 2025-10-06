@echo off
echo =========================================
echo   CS GAUNTLET - QUICK DEPLOY SCRIPT
echo =========================================
echo.

echo Step 1: Installing frontend dependencies...
cd frontend
call npm install
echo.

echo Step 2: Building frontend for production...
call npm run build
echo.

echo Step 3: Frontend build complete!
echo.

echo =========================================
echo   DEPLOY OPTIONS:
echo =========================================
echo.
echo 1. VERCEL (Recommended - Fastest):
echo    Run: vercel
echo.
echo 2. NETLIFY:
echo    Run: netlify deploy --prod --dir=dist
echo.
echo 3. SURGE (Simplest):
echo    Run: npx surge dist cs-gauntlet.surge.sh
echo.
echo 4. GITHUB PAGES:
echo    Push to GitHub and enable Pages
echo.
echo =========================================
echo.
echo Your frontend is ready in: frontend\dist
echo.
pause
