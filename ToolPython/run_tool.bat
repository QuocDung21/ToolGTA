@echo off
title Auto Fishing Tool - Lu Quy RP
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo [ERROR] Ung dung bi dong voi loi. Nhan phim bat ky de thoat...
    pause >nul
)
