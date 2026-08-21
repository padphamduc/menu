@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ==========================================
echo   PUSH TO padphamduc/menu
echo ==========================================
echo.

if not exist ".git" (
    git init
    git branch -M main
    git remote add origin https://github.com/padphamduc/menu.git
) else (
    git remote remove origin >nul 2>nul
    git remote add origin https://github.com/padphamduc/menu.git
    git branch -M main
)

git add -A
git commit -m "Update DucTool launcher and tools"
git push -u origin main --force

echo.
echo Xong.
pause
