@echo off
echo =========================================
echo   SETTING UP GITHUB FOR CS GAUNTLET
echo =========================================
echo.

echo Step 1: Adding GitHub remote...
git remote add origin "https://github.com/Normboy1/cs-gauntlet.git"

echo Step 2: Setting main branch...
git branch -M main

echo Step 3: Pushing to GitHub...
git push -u origin main

echo.
echo =========================================
echo   SUCCESS! 
echo =========================================
echo.
echo Your repository is now at:
echo https://github.com/Normboy1/cs-gauntlet
echo.
echo Next: Enable GitHub Pages
echo 1. Go to: https://github.com/Normboy1/cs-gauntlet/settings/pages
echo 2. Source: Deploy from a branch
echo 3. Branch: main
echo 4. Folder: / (root)
echo 5. Save
echo.
echo Your site will be live at:
echo https://normboy1.github.io/cs-gauntlet
echo.
pause
