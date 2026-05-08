@echo off
chcp 65001 >nul
echo ========================================
echo   Start Chrome Debug Mode
echo ========================================
echo.

echo [Step 1] Closing all Chrome...
taskkill /f /im chrome.exe 2>nul
timeout /t 3 >nul

echo [Step 2] Starting Chrome with debug port...
start "" "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%TEMP%\chrome_debug_profile" "https://tidal.com" "https://mail.xoxome.online/dashboard"

echo.
echo [Done] Chrome started with debug port 9222
echo.
echo Two tabs should open:
echo   1. tidal.com
echo   2. mail.xoxome.online
echo.
echo Now run: python main_attach.py
echo.
pause
