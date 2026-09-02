@echo off
chcp 65001 >nul
cd /d "%~dp0"

py -3.12 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements-build.txt

if not exist assets\7zr.exe (
    echo Dang tai 7zr.exe chinh thuc cua 7-Zip...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri 'https://www.7-zip.org/a/7zr.exe' -OutFile 'assets\7zr.exe'"
    if errorlevel 1 (
        echo Khong tai duoc assets\7zr.exe
        pause
        exit /b 1
    )
)

pyinstaller --noconfirm --clean DucTool.spec

echo.
echo ==========================================
echo EXE: dist\DucTool.exe
echo ==========================================
pause
