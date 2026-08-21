@echo off
chcp 65001 >nul
cd /d "%~dp0"

where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "%~dp0launcher.py"
    exit
)

where python >nul 2>nul
if %errorlevel%==0 (
    start "" python "%~dp0launcher.py"
    exit
)

echo.
echo Khong tim thay Python trong PATH.
echo Hay cai Python va tick "Add Python to PATH".
echo.
pause
