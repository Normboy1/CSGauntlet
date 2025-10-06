@echo off
echo Starting CS Gauntlet Frontend Development Server...
cd /d "%~dp0"
npx vite --port 3000 --host
