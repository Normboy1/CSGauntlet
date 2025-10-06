@echo off
echo =========================================
echo   DEPLOYING CS GAUNTLET TO GITHUB
echo   Repository: Normboy1/cs-gauntlet
echo =========================================
echo.

REM Add GitHub remote
echo Adding GitHub remote...
git remote add origin https://github.com/Normboy1/cs-gauntlet.git

REM Set main branch
echo Setting up main branch...
git branch -M main

REM Push to GitHub
echo Pushing to GitHub...
git push -u origin main

echo.
echo =========================================
echo   SUCCESS! PROJECT PUSHED TO GITHUB
echo =========================================
echo.
echo Your repository is now live at:
echo https://github.com/Normboy1/cs-gauntlet
echo.
echo Next steps:
echo 1. Go to your GitHub repository
echo 2. Enable GitHub Pages in Settings
echo 3. Or deploy to Vercel/Netlify for instant hosting
echo.

echo =========================================
echo   QUICK DEPLOYMENT OPTIONS
echo =========================================
echo.
echo OPTION 1 - GitHub Pages (Free):
echo 1. Go to: https://github.com/Normboy1/cs-gauntlet/settings/pages
echo 2. Source: Deploy from a branch
echo 3. Branch: main / / (root)
echo 4. Save
echo 5. Your site will be live at: https://normboy1.github.io/cs-gauntlet
echo.
echo OPTION 2 - Vercel (Fastest):
echo 1. cd frontend
echo 2. npx vercel
echo 3. Follow prompts
echo.
echo OPTION 3 - Netlify Drop (Instant):
echo 1. Go to: https://app.netlify.com/drop
echo 2. Drag frontend folder to browser
echo.
pause
