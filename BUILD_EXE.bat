@echo off
chcp 65001 >nul
cd /d "%~dp0"

py -3.12 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements-build.txt
pyinstaller --noconfirm --clean DucTool.spec

echo.
echo ==========================================
echo EXE: dist\DucTool.exe
echo ==========================================
pause
