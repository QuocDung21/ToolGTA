@echo off
set "PATH=C:\Program Files\Microsoft Visual Studio\18\Community\Common7\IDE\CommonExtensions\Microsoft\TeamFoundation\Team Explorer\Git\cmd;%PATH%"
cd /d "%~dp0"
echo ========================================================
echo   Dang day (push) ma nguon va tag len GitHub...
echo ========================================================
echo.
git push -u origin main
git push --tags
echo.
echo Hoan tat!
pause
