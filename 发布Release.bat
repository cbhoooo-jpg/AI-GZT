@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   AI-GZT v1.0 Release Uploader (~199 MB)
echo ============================================
echo.
echo  Uploading installer to GitHub Release v1.0 ...
echo  Auto retry up to 6 times on network failure.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0发布GitHubRelease.ps1" -Step Upload
echo.
echo ============================================
echo  Finished. Check the window output above.
echo  Release page:
echo  https://github.com/cbhoooo-jpg/AI-GZT/releases
echo ============================================
pause