@echo off
echo =========================================
echo   CS GAUNTLET - GITHUB PUSH SCRIPT
echo =========================================
echo.

REM Initialize git if not already
if not exist .git (
    echo Initializing Git repository...
    git init
)

REM Rename README for GitHub
if exist README_GITHUB.md (
    echo Preparing README for GitHub...
    copy /Y README_GITHUB.md README.md
)

REM Add all files respecting .gitignore
echo.
echo Adding files to Git...
git add .

REM Show what will be committed
echo.
echo Files to be committed:
git status --short

REM Commit
echo.
set /p commit_msg="Enter commit message (or press Enter for default): "
if "%commit_msg%"=="" set commit_msg=Initial commit: CS Gauntlet with Ollama AI grading

git commit -m "%commit_msg%"

REM Add remote
echo.
echo =========================================
echo   GITHUB REMOTE SETUP
echo =========================================
echo.
echo Create a new repository on GitHub first:
echo 1. Go to https://github.com/new
echo 2. Name it: cs-gauntlet
echo 3. Keep it public or private (your choice)
echo 4. DON'T initialize with README, .gitignore, or license
echo.
set /p remote_url="Enter your GitHub repository URL (e.g., https://github.com/yourusername/cs-gauntlet.git): "

if not "%remote_url%"=="" (
    git remote add origin %remote_url%
    
    echo.
    echo Pushing to GitHub...
    git branch -M main
    git push -u origin main
    
    echo.
    echo =========================================
    echo   SUCCESS!
    echo =========================================
    echo Your project is now on GitHub!
    echo.
    echo Repository URL: %remote_url%
    echo.
    echo Next steps:
    echo 1. Visit your repository on GitHub
    echo 2. Add topics: competitive-programming, ai, ollama, flask, react
    echo 3. Add a description: Real-time competitive programming platform with AI grading
    echo 4. Star your own repository!
) else (
    echo.
    echo Push cancelled. To push later, run:
    echo git remote add origin YOUR_REPO_URL
    echo git push -u origin main
)

echo.
pause
