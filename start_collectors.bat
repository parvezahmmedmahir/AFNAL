@echo off
echo ========================================
echo  OTC Data Collection System Launcher
echo ========================================
echo.

echo [1/4] Starting Dashboard Server...
start "Dashboard Server" cmd /k "python dashboard_server.py"
timeout /t 5 /nobreak >nul

echo [2/4] Starting Recent History Collector...
start "Recent History" cmd /k "cd collectors && node 1_recent_history.js"
timeout /t 2 /nobreak >nul

echo [3/4] Starting Daily Cycle Collector...
start "Daily Cycle" cmd /k "cd collectors && node 2_daily_cycle.js"
timeout /t 2 /nobreak >nul

echo [4/6] Starting Monthly Archive Collector...
start "Monthly Archive" cmd /k "cd collectors && node 3_monthly_archive.js"
timeout /t 2 /nobreak >nul

echo [5/6] Starting OTC Harvester Engine...
start "OTC Harvester" cmd /k "python otc_harvester.py"
timeout /t 5 /nobreak >nul

echo [6/6] Starting REST API Server...
start "REST API Server" cmd /k "python api_server.py"
timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo  All systems started successfully!
echo ========================================
echo.
echo Data Collection: Running
echo REST API: http://127.0.0.1:8001
echo API Docs: http://127.0.0.1:8001/docs
echo WebSocket: ws://127.0.0.1:8000/ws
echo.
echo Check the opened windows for status.
echo Press any key to close this launcher...
pause >nul
