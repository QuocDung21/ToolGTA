@echo off
cd /d "%~dp0ToolRS\target\release"
if not exist "autofish-rs.exe" (
    echo [THONG BAO] Chua thay file autofish-rs.exe, dang bat dau build...
    call "%~dp0build.bat"
)
start "" "autofish-rs.exe"
