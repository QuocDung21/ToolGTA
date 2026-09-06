@echo off
set "PATH=C:\Program Files\Microsoft Visual Studio\18\Community\Common7\IDE\CommonExtensions\Microsoft\TeamFoundation\Team Explorer\Git\cmd;%PATH%"
cd /d "%~dp0"
echo ========================================================
echo   Dang day (push) ma nguon len GitHub (ToolGTA)...
echo   Neu trinh duyet mo len, hay nhan xac thuc GitHub!
echo ========================================================
echo.
git push -u origin main
echo.
pause
