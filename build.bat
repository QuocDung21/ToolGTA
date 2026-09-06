@echo off
set "PATH=C:\Users\ADMIN\w64devkit\bin;C:\Users\ADMIN\.cargo\bin;%PATH%"
cd /d "%~dp0ToolRS"
echo [1/2] Dang build ban Release...
cargo build --release
if %ERRORLEVEL% NEQ 0 (
    echo [LOI] Build that bai!
    pause
    exit /b %ERRORLEVEL%
)

echo [2/2] Dong bo thu muc assets va config...
xcopy /E /I /Y "assets" "target\release\assets" >nul
xcopy /E /I /Y "config" "target\release\config" >nul

echo.
echo =======================================================
echo   Build hoan tat thanh cong!
echo   File thuc thi: ToolRS\target\release\autofish-rs.exe
echo =======================================================
pause
