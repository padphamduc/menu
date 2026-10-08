@echo off
chcp 65001 >nul
title Tool v3.1 Dùng Chuột ( Thêm tính năng hiển thị đáp án tự luận )
cd /d "C:\duc\tools\seb_mouse_v31"
python main.py
if errorlevel 1 (
    echo.
    echo Có lỗi khi chạy tool. Nhấn phím bất kỳ để đóng...
    pause >nul
)
