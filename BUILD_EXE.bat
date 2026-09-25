@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ==========================================
echo       TIẾN HÀNH BUILD APP (DUCTOOL)
echo ==========================================
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo [1/3] Đang tạo môi trường ảo Python 3.12...
    py -3.12 -m venv .venv
    if errorlevel 1 (
        echo Không tìm thấy Python 3.12, thử dùng lệnh python mặc định...
        python -m venv .venv
    )
) else (
    echo [1/3] Đã có sẵn môi trường ảo .venv.
)

call .venv\Scripts\activate.bat

echo [2/3] Đang kiểm tra và cài đặt thư viện build...
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements-build.txt

echo [3/3] Đang đóng gói ứng dụng bằng PyInstaller...
pyinstaller --noconfirm --clean DucTool.spec

echo.
if exist "dist\DucTool.exe" (
    echo ==========================================
    echo   BUILD APP THÀNH CÔNG!
    echo   File chạy: dist\DucTool.exe
    echo ==========================================
) else (
    echo ==========================================
    echo   BUILD APP THẤT BẠI! Vui lòng kiểm tra lỗi ở trên.
    echo ==========================================
)

pause
